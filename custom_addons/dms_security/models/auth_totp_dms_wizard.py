from odoo import models, api
from odoo.http import request


class AuthTotpDMSWizard(models.TransientModel):
    _inherit = 'auth_totp.dms.wizard'

    @api.depends('user_id', 'secret')
    def _compute_url(self):
        super()._compute_url()  # call original to ensure fields are available
        for wizard in self:
            if wizard.user_id and wizard.secret:
                base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                domain = base_url.split("//")[-1]  # extract domain part (e.g., 'mydomain.com')

                login = wizard.user_id.login
                issuer = f"{domain} - {login}"

                totp_uri = wizard.user_id._get_totp_uri(secret=wizard.secret.replace(' ', ''), issuer=domain)
                wizard.url = totp_uri
