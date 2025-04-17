from odoo import _, api, fields, models
import base64
import os
from odoo.addons.auth_totp.models.totp import TOTP, TOTP_SECRET_SIZE
from odoo.exceptions import AccessDenied, UserError
import logging
from odoo.http import request

_logger = logging.getLogger(__name__)


class DMSDirectorySecurity(models.Model):
    _inherit = 'dms.directory'

    dms_security_id = fields.Many2one(comodel_name='dms.security', string='Security Option',
                                      compute='_compute_security_option', store=True)
    is_security_required = fields.Boolean('Requires Security?', related='dms_security_id.is_required', readonly=True,
                                          store=True)
    active_security = fields.Boolean('Security Enabled', default=False)
    security_user_id = fields.Many2one(comodel_name='res.users', string='Added by', related='dms_security_id.user_id',
                                       readonly=True, store=True)
    totp_secret = fields.Char(string="TOTP Secret", copy=False)

    is_unlocked = fields.Boolean(
        string="Unlocked",
        default=False,
        help="Indicates if the directory has been unlocked by the user."
    )

    def action_unlock_directory(self):
        """ Unlock the directory so files inside become accessible """
        for record in self:
            if record.active_security:
                record.is_unlocked = True

    def user_has_access(self):
        """ Check if the user has unlocked the secured directory """
        return self.is_unlocked

    @api.depends('active_security')
    def _compute_security_option(self):
        for record in self:
            if not record.active_security:
                record.dms_security_id = False

    def action_open_kanban_authenticator(self):
        """ Trigger Google Authenticator for directory access """
        self.ensure_one()

        # If security is disabled, open the directory directly
        if not self.active_security:
            return self._open_directory_view()

        # If user does not have permission
        if self.env.user.id != self.dms_security_id.user_id.id:
            raise UserError(_("You do not have permission to access this directory."))

        # If Google 2FA is required
        if self.dms_security_id.selection == 'g2fa':
            return self._authenticate_google_2fa()

        # Default case: open the directory
        return self._open_directory_view()

    def _authenticate_google_2fa(self):
        """ Google 2FA authentication process """
        self.ensure_one()
        if not self.totp_secret:
            raise UserError(_("Google 2FA is not configured for this directory."))

        # Return authentication form
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'auth_totp.dms.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_user_id': self.env.user.id, 'default_directory_id': self.id}
        }

    def _open_directory_view(self):
        """ Open directory if authentication is passed """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('DMS Directory'),
            'res_model': 'dms.directory',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    def _authenticate_google_2fa(self):
        """ Google 2FA authentication process """
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('dms.action_dms_authenticator_kanban')
        return action

    def enable_totp(self):
        """ Generate a new TOTP secret and enable 2FA """
        secret_bytes_count = TOTP_SECRET_SIZE // 8
        self.totp_secret = base64.b32encode(os.urandom(secret_bytes_count)).decode()
        self.active_security = True
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _("Google 2FA is now enabled for this directory."),
            }
        }

    def disable_totp(self):
        """ Disable Google 2FA for this directory """
        self.totp_secret = ''
        self.active_security = False
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'warning',
                'message': _("Google 2FA is now disabled for this directory."),
            }
        }
