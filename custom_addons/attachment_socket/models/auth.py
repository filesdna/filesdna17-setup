# models/auth_token.py
from odoo import models, fields, api
from datetime import datetime, timedelta
import base64
import os

class AuthToken(models.Model):
    _name = 'auth.token'
    _description = 'Authentication Token'

    name = fields.Char('Token', required=True, unique=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    expiration_date = fields.Datetime('Expiration Date')

    @api.model
    def create_or_update_token(self, user):
        """Create or update a token for a user"""
        expiration_date = datetime.now() + timedelta(days=7)  
        token = self.sudo().search([('user_id', '=', user.id)], limit=1)
        if token:
            token.write({
                'expiration_date': expiration_date,
            })
        else:
            self.create({
                'name': self._generate_token(),
                'user_id': user.id,
                'expiration_date': expiration_date,
            })

    def _generate_token(self):
        """Generate a random token string"""
        return base64.urlsafe_b64encode(os.urandom(24)).decode()

    @api.model
    def is_valid_token(self, token):
        """Check if a token is valid"""
        token_record = self.sudo().search([('name', '=', token)], limit=1)
        if token_record and (not token_record.expiration_date or token_record.expiration_date > fields.Datetime.now()):
            return True
        return False

    @api.model
    def cron_update_tokens(self):
        users = self.sudo().env['res.users'].search([])
        for user in users:
            self.create_or_update_token(user)
