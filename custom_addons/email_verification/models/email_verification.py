#  -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2018-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE URL <https://store.webkul.com/license.html/> for full copyright and licensing details.
#################################################################################

from odoo import api, fields, models, _
from odoo.addons.auth_signup.models.res_partner import now
from odoo.http import request
import logging
_logger = logging.getLogger(__name__)

class ResUsers(models.Model):
    _inherit = 'res.users'

    wk_token_verified = fields.Boolean(
        string='Token Verified', default=True)

    @api.model
    def send_verification_email(self, res_id):
        user = self.browse(res_id)
        validity = self.env['website'].get_current_website().token_validity
        expiration = now(days=+validity)
        temp_id = self.env.ref('email_verification.wk_email_verification_email_template_id')
        user.partner_id.signup_prepare(signup_type="verify", expiration=expiration)
        if temp_id:
            try:
                if self.env.context.get('website'):
                    res = temp_id.with_context(website=self.env.context.get('website')).send_mail(res_id, email_values={'email_to': user.partner_id.email or ''})
                    current_mail = self.env['mail.mail'].browse(res)
                    res=current_mail.send()
                else:
                    res = temp_id.send_mail(res_id, email_values={'email_to': user.partner_id.email or ''})
                    current_mail = self.env['mail.mail'].browse(res)
                    res=current_mail.send()
            except Exception as e:
                _logger.info('=======Exception======== {}'.format(e))
        return True

    @api.model
    def create(self, vals):
        flag_website, website = False, False
        if vals.get('signup_from_website', False):
            flag_website = True
            vals.pop('signup_from_website')
        if vals.get('website', False):
            website = vals.get('website')
            vals.pop('website')
        vals['wk_token_verified'] = False
        res_id = super(ResUsers, self).create(vals)
        if flag_website:
            if website:
                self.with_context(website=website).send_verification_email(res_id.id)
            else:
                self.send_verification_email(res_id.id)
        return res_id

    def write(self, vals):
        if vals.get('signup_from_website', False):
            vals.pop('signup_from_website')
        return super(ResUsers, self).write(vals)

    @api.model
    def get_verification_url(self):
        db = self._cr.dbname
        if self.signup_token and db:
            website_id = False
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            if self.env.context.get('website', False):
                website_id = self.env['website'].browse(int(self.env.context.get('website')))
                if website_id:
                    htty_type = 'http://'
                    if 'https' in base_url:
                        htty_type = 'https://'
                    if website_id.domain:
                        base_url = website_id.domain
                    if not 'https' in base_url and not 'http' in base_url:
                        base_url = htty_type + base_url
            redirect_url = '/web/login'
            url = "%s/web/email/verification?db=%s&wk_token=%s&wk_uid=%s"%(base_url, db,self.signup_token,self.id)
            return url
        return False

    @api.model
    def wk_verify_email(self, params={}):
        status = 'error'
        msg = "Oops!!. There is some error currently please try after some time."
        try:
            if params.get('wk_token') and params.get('wk_uid') and params.get('db'):
                uid = int(params.get('wk_uid'))
                token = str(params.get('wk_token'))
                user = request.env['res.users'].sudo().browse(uid)
                msg = "Your account has been verified. You will be automatically redirected to Home page."
                if not user.wk_token_verified:
                    if user.signup_token == token:
                        if not user.signup_valid:
                            status = 'expired'
                            msg = "This link has been expired. Resend a new verification link from your account."
                        else:
                            user.wk_token_verified = True
                            status = 'verified'
                    else:
                        status = 'unverified'
                        msg = "The account is not verified yet. Resend a new verification link from your account."
                else:
                    status = 'already_verified'
                    msg = "Your account has already been verified. You will be automatically redirected to Home page."
        except Exception as e:
            status = 'error'
            msg = "Oops!!. There is some error currently please try after some time."
        return {'status':status,'msg':msg}


    def resend_verification_user_email(self):
        msg =  "A new email has been sent to this user successfully."
        res = self.send_verification_email(self.id)
        if not res:
            msg = 'Exception in sending the email. Please try again later.'
        wizard_id = self.env['wizard.message'].create(
                {'text': msg})
        return {'name': _("Summary"),
                'view_mode': 'form',
                'view_id': False,
                'res_model': 'wizard.message',
                'res_id': wizard_id.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': '[]',
                }


    def verify_email_manually(self):
        self.wk_token_verified = True
        wizard_id = self.env['wizard.message'].create(
                {'text': "Email has been verified manually!!"})
        return {'name': _("Summary"),
                'view_mode': 'form',
                'view_id': False,
                # 'view_type': 'form',
                'res_model': 'wizard.message',
                'res_id': wizard_id.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': '[]',
                }

class Partner(models.Model):
    _inherit = 'res.partner'

    def write(self, vals):
        if vals.get('email',None) and vals.get('email')!=self.email:
            current_user = self.env['res.users'].sudo().browse(self._uid)
            current_user.wk_token_verified = False
            res = super(Partner,self).write(vals)
            current_user.send_verification_email(self._uid)
        else:
            res = super(Partner,self).write(vals)
        return res
