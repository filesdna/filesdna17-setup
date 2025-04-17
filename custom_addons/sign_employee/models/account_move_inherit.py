from odoo import api, fields, models, _


class BSAccountMove(models.Model):
    _inherit = 'account.move'

    bem_ref = fields.Char('BEM Reference')
