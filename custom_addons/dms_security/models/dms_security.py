# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons.auth_totp.models.totp import TOTP, TOTP_SECRET_SIZE
import base64
from odoo.exceptions import AccessDenied, UserError
import os
from odoo.http import request
import requests
import json
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import firebase_admin
from firebase_admin import credentials
import logging
_logger = logging.getLogger(__name__)


class DMSSecurity(models.Model):
    _name = 'dms.security'
    _description = 'DMS Security Options'



    security_options = [
        ('g2fa', 'Google 2FA/Microsoft 2FA'),
        ('fp', 'Fingerprint'),
        ('nfc', 'NFC'),
        ('ma', 'Mobile Authentication'),
        ('sms', 'SMS Coming Soon'),
    ]
    name =  fields.Char('Name')
    selection = fields.Selection(
        security_options,
        string='Secuirty Option',
        help='Select the Secuirty Option You need.',
    )
    is_required = fields.Boolean("Status")
    user_id = fields.Many2one(comodel_name='res.users', string='User')
    notification_status = fields.Selection([
        ('pending', 'Pending'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed')
    ], default='pending') 
    
    @api.model
    def create_security_option(self, user):
        security_options = [
        ('g2fa', 'Google 2FA/Microsoft 2FA'),
        ('fp', 'Fingerprint'),
        ('nfc', 'NFC'),
        ('ma', 'Mobile Authentication'),
        ('sms', 'SMS')
        
    ]
        for record in security_options:
            self.create({
                'name':record[1],
                "user_id":user.id,
                "selection":record[0],
                "is_required":False,

            })


    @api.model
    def cron_update_tokens(self):
        users = self.sudo().env['res.users'].search([])
        for user in users:
            check_record = self.env['dms.security'].search([('user_id', '=', user.id)])
            if not check_record and user:
                self.create_security_option(user)


    def action_totp_enable_wizard_dms(self):
        if self.selection == 'g2fa':
            if self.env.user != self.env.user:
                raise UserError(_("Two-factor authentication can only be enabled for yourself"))

            secret_bytes_count = TOTP_SECRET_SIZE // 8
            secret = base64.b32encode(os.urandom(secret_bytes_count)).decode()
            # format secret in groups of 4 characters for readability
            secret = ' '.join(map(''.join, zip(*[iter(secret)]*4)))
            w = self.env['auth_totp.dms.wizard'].sudo().create({
                'user_id': self.env.user.id,
                'secret': secret,
            })

            return {
                'type': 'ir.actions.act_window',
                'target': 'new',
                'res_model': 'auth_totp.dms.wizard',
                'name': _("Two-Factor Authentication Activation For DMS"),
                'res_id': w.id,
                'views': [(False, 'form')],
                'context': self.env.context,
            }
        token = self.env.user.firebase_token
        
        if self.selection == 'fp':
            message_id = self.env['message.wizard'].create({'message': _("Press allow on your mobile app to open this file")})
            return {
                    'type': 'ir.actions.client',
                    'tag': 'activate_security',
                    'params': {
                        'record_id': self.id,
                        'message_id': message_id.id,
                    }
                }
        if self.selection == 'nfc':
            message_id = self.env['message.wizard'].create({'message': _("Pass your Card on your phone to activate")})
            return {
                            'type': 'ir.actions.client',
                            'tag': 'activate_security',
                            'params': {
                                'record_id': self.id,
                                'message_id': message_id.id,
                            }
                        }
        if self.selection == 'ma':
            message_id = self.env['message.wizard'].create({'message': _("Press allow on your phone to open activate")})
            return {
                            'type': 'ir.actions.client',
                            'tag': 'activate_security',
                            'params': {
                                'record_id': self.id,
                                'message_id': message_id.id,
                            }
                        }

            

    def action_totp_disable_dms(self):
        if self.selection == 'fp':
            self.is_required = False
        if self.selection == 'nfc':
            self.is_required = False
        if self.selection == 'ma':
            self.is_required = False
        if self.selection == 'g2fa':
            if not (self.user_id == self.env.user or self.user_id._is_admin() or self.env.su):
                return False

            self.user_id.revoke_all_devices()
            self.user_id.sudo().write({'totp_secret_dms': False})

            if request and self.user_id == self.env.user:
                self.env.flush_all()
                # update session token so the user does not get logged out (cache cleared by change)
                new_token = self.env.user._compute_session_token(request.session.sid)
                request.session.session_token = new_token
            self.is_required = False

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': _("Two-factor authentication disabled for the following user : %s", self.user_id.name),
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }


# ----------------------------------- method for firebase push notification ------------------------------------------------
    
    def fcm_method(self, method, message):
        # Path to your service account key JSON file
        service_account_key = '/opt/filesdna17/custom_addons/serviceAccountKey.json'
        # Replace with your Firebase project ID
        project_id = 'filesdna'
        # FCM v1 API URL
        url = f'https://fcm.googleapis.com/v1/projects/{project_id}/messages:send'
        # Create a service account credentials object
        credentials = service_account.Credentials.from_service_account_file(
            service_account_key, 
            scopes=['https://www.googleapis.com/auth/firebase.messaging']
        )
        # Refresh the token and obtain an OAuth2 access token
        credentials.refresh(Request())
        access_token = credentials.token
        # Set up the notification data
        title = "FilesDNA"
        body = {'type': method}
        # Set the headers with OAuth2 token
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }
        # Create the payload for the FCM v1 API request
        payload = json.dumps({
            'message': {
                'token': self.env.user.firebase_token,  # Device token
                'notification': {
                    'title': title,
                    'body': message,
                },
                'data': body
            }
        })
        # Send the notification request
        response = requests.post(url, data=payload, headers=headers)
        _logger.info('Fire Base response....... %s',response.text)
        # Check the response status
        if response.status_code == 200:
            return True
        else:
            # print(f'Error: {response.status_code}, {response.text}')
            return False