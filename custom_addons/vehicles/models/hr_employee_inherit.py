from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    vehicles_id = fields.Many2one('vehicles')

