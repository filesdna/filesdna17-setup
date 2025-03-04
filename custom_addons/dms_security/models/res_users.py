# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import functools
import io
import qrcode
import re
import werkzeug.urls
import logging
from odoo.exceptions import AccessDenied, UserError

from odoo import _, api, fields, models
from odoo.addons.base.models.res_users import check_identity
from odoo.exceptions import UserError
from odoo.http import request
from odoo.addons.auth_totp.models.totp import TOTP, TOTP_SECRET_SIZE
from odoo.addons.auth_totp.models.totp import ALGORITHM, DIGITS, TIMESTEP
_logger = logging.getLogger(__name__)

class RESUSERSecret(models.Model):
    _inherit = 'res.users'
    
    totp_secret_dms = fields.Char(copy=False, groups=fields.NO_ACCESS, compute='_compute_totp_secret_dms', inverse='_inverse_token_dms',store=True)
    firebase_token = fields.Char(string='FCM',readonly=True,store=True)
# ----------------------------------------- nfc -------------------------------------------------------------------------------------
    nfc_line_ids  = fields.One2many(comodel_name='res.users.nfc', inverse_name='user_id', string='NFC Cards')
    

    def _inverse_token_dms(self):
        for user in self:
            secret = user.totp_secret_dms if user.totp_secret_dms else None
            self.env.cr.execute('UPDATE res_users SET totp_secret_dms = %s WHERE id=%s', (secret, user.id))

    def _compute_totp_secret_dms(self):
        for user in self:
            self.env.cr.execute('SELECT totp_secret_dms FROM res_users WHERE id=%s', (user.id,))
            user.totp_secret_dms = self.env.cr.fetchone()[0]

    def _totp_check_dms(self, code):
        sudo = self.env.user.sudo()
        key = base64.b32decode(sudo.totp_secret_dms)
        match = TOTP(key).match(code)
        if match is None:
            _logger.info("2FA check: FAIL for %s %r", self, sudo.login)
            raise AccessDenied(_("Verification failed, please double-check the 6-digit code"))
        _logger.info("2FA check: SUCCESS for %s %r", self, sudo.login)



    @api.model
    def create(self, values):
        result = super(RESUSERSecret, self).create(values)
        self.env['dms.security'].cron_update_tokens()
        return result