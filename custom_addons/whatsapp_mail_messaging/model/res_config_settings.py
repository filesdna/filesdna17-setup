# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """
    Extends the 'res.config.settings' model to include additional configuration settings.
    """
    _inherit = 'res.config.settings'

    whatsapp_message = fields.Text(string="Message Template",
                                   related='company_id.whatsapp_message',
                                   readonly=False)
