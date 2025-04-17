from odoo import _, api, fields, models, tools

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_ocn = fields.Boolean("Enable OCN")
