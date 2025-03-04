# -*- coding: utf-8 -*-

from odoo import models, fields, api


class EmployeeTaxRule(models.Model):
    _name = 'employee.tax.rule'
    _description = 'Employee Tax Rule'

    name = fields.Char('Allow Name')
    amount = fields.Float('Allow Amount',
    digits=(6, 0)
    )

class EmployeeTaxCalculation(models.Model):
    _name = 'employee.tax.amount'
    _description = 'Employee Tax Rule'


    name = fields.Char()
    amonut = fields.Float(string='Amount to deduact from ', digits=(6, 0))
    percentage = fields.Float(string='Tax Percentage')

