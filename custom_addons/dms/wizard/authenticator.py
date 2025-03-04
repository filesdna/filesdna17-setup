# -*- coding: utf-8 -*-
import re
from odoo import fields, models, api, _
from odoo.exceptions import AccessDenied

class DmsAuthenticator(models.TransientModel):
    _name = "dms.authenticator"
    _description = "Authentication Wizaed"

    record_id = fields.Char(string='record')
    code = fields.Char(string='Authentication Code')

    def authenticate(self):
        try:
            with self.env.user._assert_can_auth(user=self.env.user.id):
                self.env.user._totp_check_dms(int(re.sub(r'\s', '', self.code)))
        except AccessDenied as e:
            error = str(e)
            raise AccessDenied(_("Verification failed, please double-check the 6-digit code"))
        except ValueError:
            error = _("Invalid authentication code format.")
        else:
            res_model_record = self.env.context
            file = self.env[res_model_record['active_model']].sudo().search([('id','=',res_model_record['active_id'])])
            groups = file.directory_id.complete_group_ids.ids
            file.has_permission(groups_ids=groups, permission='perm_lock')
            file.decrypt_content()
            file.write({"locked_by": None, 'is_locked': False})
            return {
                'effect': {
                    'fadeout': 'fast',
                    'message': 'Successfully Passed.',
                    'type': 'rainbow_man',
                }
            }
    
    def action_kanban_authenticate(self):
        try:
            with self.env.user._assert_can_auth(user=self.env.user.id):
                self.env.user._totp_check_dms(int(re.sub(r'\s', '', self.code)))
        except AccessDenied as e:
            error = str(e)
            raise AccessDenied(_("Verification failed, please double-check the 6-digit code"))
        except ValueError:
            error = _("Invalid authentication code format.")
        else:
            res_model_record = self.env.context
            file = self.env[res_model_record['active_model']].sudo().search([('id', '=', res_model_record['active_id'])])
            action = {
                'type': 'ir.actions.act_window',
                'name': _('DMS File'),
                'res_model': 'dms.file',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': file.id,
                'target': 'current',
            }
            return action

    