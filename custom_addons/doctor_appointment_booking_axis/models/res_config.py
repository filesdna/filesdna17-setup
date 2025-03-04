# Copyright 2016 Tecnativa - Antonio Espinosa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    is_single_booking = fields.Boolean("Is Single Booking",default=False)


class WebsiteConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_single_booking = fields.Boolean("Is Single Booking",related='company_id.is_single_booking',store=True,readonly=False)

    def get_values(self):
        res = super(WebsiteConfigSettings, self).get_values()
        res.update(is_single_booking=self.env['ir.config_parameter'].sudo().get_param('is_single_booking'))
        return res

    def set_values(self):
        super(WebsiteConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('is_single_booking', self.is_single_booking)