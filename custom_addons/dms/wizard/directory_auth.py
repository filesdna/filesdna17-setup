# -*- coding: utf-8 -*-
import re
from odoo import fields, models, api, _
from odoo.exceptions import AccessDenied
import logging

_logger = logging.getLogger(__name__)

class DmsDirectoryAuthenticator(models.TransientModel):
    _name = "dms.directory.authenticator"
    _description = "Authentication Wizard"

    record_id = fields.Char(string='record')
    code = fields.Char(string='Authentication Code')   

    def authenticate_directory(self):
        try:
            with self.env.user._assert_can_auth(user=self.env.user.id):
                self.env.user._totp_check_dms(int(re.sub(r'\s', '', self.code)))
        except AccessDenied as e:
            error = str(e)
            raise AccessDenied(_("Verification failed, please double-check the 6-digit code"))
        except ValueError:
            error = _("Invalid authentication code format.")
        else:
            return {
                'effect': {
                    'fadeout': 'fast',
                    'message': 'Successfully Passed.',
                    'type': 'rainbow_man',
                }
            }