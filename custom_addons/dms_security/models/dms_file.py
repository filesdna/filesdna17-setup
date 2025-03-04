# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
import time
import json 
import requests
from odoo import models, fields, api, _
from odoo.addons.auth_totp.models.totp import TOTP, TOTP_SECRET_SIZE
import base64
from odoo.exceptions import AccessDenied, UserError
import os
from odoo.http import request
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import firebase_admin
from firebase_admin import credentials
import logging

_logger = logging.getLogger(__name__)



class DMSFileSecurity(models.Model):
    _inherit = 'dms.file'


    dms_security_id = fields.Many2one(comodel_name='dms.security', string='Security Option',compute='onchange_security_user_id', store=True)
    is_security_required  = fields.Boolean('Status',
    related='dms_security_id.is_required',
    readonly=True,
    store=True,
    default=False
    )
    
    notification_status = fields.Selection([
        ('pending', 'Pending'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed')
    ], default='pending')
    mobile_response = fields.Char('Mobile Response')
    active_security = fields.Boolean('Status',default=False)
    security_user_id = fields.Many2one(comodel_name='res.users', string='Added by',
                related='dms_security_id.user_id',
                readonly=True,
                store=True,
    )
  

    @api.constrains('active_security')
    def _check_active_security(self):
        for record in self:
            if record.active_security and not record.dms_security_id:
                raise ValidationError("You Have to select security option first.")

    @api.depends('active_security')
    def onchange_security_user_id(self):
        for record in self:
            if record.active_security == False:
                record.dms_security_id = False


    # ---------------- senk -----------------------   
    def action_open_kanban_authenticator(self):
        if self.active_security:
            if self.env.user.id == self.dms_security_id.user_id.id:
                if self.dms_security_id.selection == 'g2fa':
                    self.ensure_one()
                    action = self.env['ir.actions.act_window']._for_xml_id('dms.action_dms_authenticator_kanban')
                    return action
                token = self.env.user.firebase_token
                if self.dms_security_id.selection == 'fp':
                    message_id = self.env['message.wizard'].create({'message': _("Press allow on your mobile app to open this file")})
                    return {
                            'type': 'ir.actions.client',
                            'tag': 'notification_loop',
                            'params': {
                                'record_id': self.id,
                                'message_id': message_id.id,
                            }
                        }

                if self.dms_security_id.selection == 'nfc':
                    message_id = self.env['message.wizard'].create({'message': _("Press allow on your mobile app to open this file")})
                    return {
                            'type': 'ir.actions.client',
                            'tag': 'notification_loop',
                            'params': {
                                'record_id': self.id,
                                'message_id': message_id.id,
                            }}
                                    
                if self.dms_security_id.selection == 'ma':
                    message_id = self.env['message.wizard'].create({'message': _("Press allow on your mobile app to open this file")})
                    return {
                            'type': 'ir.actions.client',
                            'tag': 'notification_loop',
                            'params': {
                                'record_id': self.id,
                                'message_id': message_id.id,
                            }
                        }

            else:
                message_id = self.env['message.wizard'].create({'message': _("This file is private you are not allow to open it")})
                return {
                    'name': _(f'Permission Deny'),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'message.wizard',
                    'res_id': message_id.id,
                    'target': 'new'
                }
        else :
            self.ensure_one()
            action = {
            'type': 'ir.actions.act_window',
            'name': _('DMS File'),
            'res_model': 'dms.file',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'target': 'current',
                }
            return action


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
        body = {
            'type': method,
            'file_id':str(self.id)
        }
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
        _logger.info('FireBase Response.... %s',response.text)
        if response.status_code == 200:
            return True
        else:
            # print(f'Error: {response.status_code}, {response.text}')
            return False
      