# -*- coding: utf-8 -*-

from odoo import models, fields, api


class EmployeeDMS(models.Model):
    _inherit = 'hr.employee'



    dms_line_ids = fields.Many2many(comodel_name='dms.file', string='Files')

