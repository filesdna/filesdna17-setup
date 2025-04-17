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

    # def authenticate_directory(self):
    #     try:
    #         with self.env.user._assert_can_auth(user=self.env.user.id):
    #             self.env.user._totp_check_dms(int(re.sub(r'\s', '', self.code)))
    #     except AccessDenied as e:
    #         error = str(e)
    #         raise AccessDenied(_("Verification failed, please double-check the 6-digit code"))
    #     except ValueError:
    #         error = _("Invalid authentication code format.")
    #     else:
    #         # Set directory_security to False
    #         user = self.env.user
    #         print('user=', user.name)
    #         # Get the list of directory names
    #         user_directories = user.access_id_many.directory_ids.mapped('name')
    #         self_directory = self.directory_id.name
    #         print('user_directory=', user.access_id_many.directory_ids.mapped('name'))
    #         print('self_directory=', self.directory_id.name)
    #         if self_directory in user_directories:
    #             print(f'self_directory="{self_directory}" is found in user_directory')
    #         else:
    #             print(f'self_directory="{self_directory}" is not found in user_directory')
    #         user.access_id_many.directory_ids.file_ids.directory_security = False
    #         print('boolean_file_false=', self.directory_id.file_ids.directory_security)
    #         return {
    #             'effect': {
    #                 'fadeout': 'fast',
    #                 'message': 'Successfully Passed.',
    #                 'type': 'rainbow_man',
    #             }
    #         }
    #
