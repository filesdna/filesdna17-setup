from odoo import models, fields, api
from datetime import date


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    sign = fields.Binary("Signature")