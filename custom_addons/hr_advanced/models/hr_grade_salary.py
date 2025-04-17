# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrGradeSalary(models.Model):
    _name = 'hr.grade.salary'

    name = fields.Char()
    basic_salary_line = fields.One2many('hr.grade.salary.line', 'basic_id')


class HrGradeSalaryLine(models.Model):
    _name = 'hr.grade.salary.line'

    grade_type = fields.Many2one('hr.employee.grade_type', string='Grade Type')
    grade = fields.Many2one('hr.employee.grade', string='Grade')
    level = fields.Many2one('hr.employee.level', string='Level')
    basic_id = fields.Many2one('hr.grade.salary')
    amount = fields.Float()
