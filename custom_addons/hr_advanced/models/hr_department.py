# -*- coding: utf-8 -*-

from odoo import models, fields, api
from lxml import etree


class EmployeeOfficeCustom(models.Model):
    _inherit = 'hr.department'

    ministry = fields.Many2one(comodel_name='hr.employee.ministry', string='Main')
    unit_level = fields.Integer(string='Unit Level')
    ref_unit = fields.Many2one(comodel_name='hr.department', string='Reference Unit')
    main_unit = fields.Many2one(comodel_name='hr.department', string='Main Unit')
    parent_unit = fields.Many2one(comodel_name='hr.department', string='Parent Unit')
    is_main = fields.Boolean('', default=False)
    unit_address = fields.Char(string='Unit Address')
    # unit_manager = fields.Many2one(comodel_name='hr.employee', string='Manager Name')
    # unit_manager_assistant=fields.Many2one(comodel_name='hr.employee', string='Debuty Manager')
