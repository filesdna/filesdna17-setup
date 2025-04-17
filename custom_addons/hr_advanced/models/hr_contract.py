# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ContractMoreDetails(models.Model):
    _inherit = 'hr.contract'

    tax = fields.Float(string='Tax', digits=(6, 0))  # الضريبة
    monthly_tax = fields.Float(string='Monthly Tax', digits=(6, 0))  # الضريبة الشهرية
    social_tax = fields.Float(string='Socail Security', digits=(6, 0),
                              compute='_compute_social_tax')
    marriage_salary = fields.Float(string='Marriage Salary', digits=(6, 0))  # راتب اضافي
    akran_salary = fields.Float(string='Akran Salary', digits=(6, 0))  # راتب اقران
    payment_method = fields.Selection([('cash', 'Cash'), ('eletronic', 'Eletronic')], default='cash')
    job_address_id = fields.Many2one('job.address', string='Job Title',
                                     related='employee_id.job_address_id',
                                     readonly=True,
                                     store=True
                                     )
    wage = fields.Monetary('Wage', required=False, tracking=True, help="Employee's monthly gross wage.",
                           group_operator="avg", readonly=0)

    @api.depends('wage')
    def _compute_social_tax(self):
        for record in self:
            record.social_tax = record.wage * .0025


class JobAdress(models.Model):
    _name = 'job.address'

    name = fields.Char('Job Address', )
    percentage = fields.Float(string='Percentage')


class ContractAllotments(models.Model):
    _name = 'hr.payslip.allotment'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip')
    allotment_id = fields.Many2one(comodel_name='hr.payslip.allotment.type', string='Allotment')
    allotment_type = fields.Selection([('percentage', 'Percentage'), ('fixed_amount', 'Fixed Amount')],
                                      related='allotment_id.allotment_type',
                                      readonly=True,
                                      store=True
                                      )
    salary_type = fields.Selection(
        [('basic', 'Basic Salary'), ('akran', 'Akran Salary'), ('marriage', 'Marriage Salary')], default='basic',
        required=True)

    percentage = fields.Float(
        string='Percentage',
        related='allotment_id.percentage',
        readonly=True,
        store=True

    )
    fixed_amount = fields.Float(
        string='Amount', digits=(6, 0),
        related='allotment_id.fixed_amount',
        readonly=True,
        store=True

    )

    num = fields.Float(string='Number Of Days', digits=(6, 0))
    total_amount = fields.Float(string='Sub Total', digits=(6, 0),
                                compute='_compute_total_allotment')

    @api.depends('allotment_id', 'slip_id.allotment_ids', 'allotment_type', 'salary_type', 'fixed_amount', 'percentage')
    def _compute_total_allotment(self):
        for record in self:
            salary = 0
            record.total_amount = 0
            salary = record.slip_id.contract_id.wage
            if record.allotment_type == 'percentage':
                if record.allotment_id.code == 'cert':
                    record.percentage = record.slip_id.employee_id.certificate_id.percentage
                    record.total_amount = record.percentage * salary
                elif record.allotment_id.code == 'title':
                    record.percentage = record.slip_id.employee_id.job_address_id.percentage
                    record.total_amount = record.percentage * salary
                else:
                    record.total_amount = (record.percentage * salary)

            if record.allotment_type == 'fixed_amount':
                if record.allotment_id.code == 'child':
                    record.total_amount = record.fixed_amount * record.slip_id.num_of_child * 1000
                elif record.allotment_id.code == 'wife' and record.slip_id.employee_id.marital == 'married':
                    record.total_amount = record.fixed_amount * 1000

                else:
                    record.total_amount = record.fixed_amount * 1000


class ContractAllotmentsType(models.Model):
    _name = 'hr.payslip.allotment.type'

    name = fields.Char(string='Allotment')
    code = fields.Char("code")
    rule_id = fields.Many2one('hr.salary.rule', string='Rule')
    allotment_type = fields.Selection([('percentage', 'Percentage'), ('fixed_amount', 'Fixed Amount')], required=True,
                                      default='fixed_amount')
    percentage = fields.Float(string='Percentage')
    fixed_amount = fields.Float(string='Amount',
                                digits=(6, 0)
                                )

    def create_rule_salary_allotment(self):
        for record in self:
            structure_id = record.env['hr.payroll.structure'].search([('id', '=', 2)])
            category_id = record.env['hr.salary.rule.category'].search([('code', '=', 'ALT')])
            rule = record.env['hr.salary.rule'].create({
                'name': record.name,
                'category_id': category_id.id,
                # 'struct_id':structure_id.id,
                'code': record.code,
                'active': True,
                'appears_on_payslip': True,
                'amount_select': 'fix',
            })
            allotment = self.env['hr.payslip.allotment.type'].search([('name', '=', rule.name)])
            print('allotment=', allotment)
            print('rule=', rule)
            for allot in allotment:
                if allot.rule_id:
                    allot.rule_id.unlink()  # This will delete the existing rule_id

            for rule_allotment in rule:
                print('rule_allotment=', rule_allotment)
                allotment.write({
                    "rule_id": rule_allotment
                })


class ContractDeductionType(models.Model):
    _name = 'hr.payslip.deduction.type'

    name = fields.Char(string='Deduction')
    code = fields.Char("code")
    rule_id = fields.Many2one('hr.salary.rule', string='Rule')
    deduction_type = fields.Selection([('percentage', 'Percentage'), ('fixed_amount', 'Fixed Amount')], required=True,
                                      default='fixed_amount')
    percentage = fields.Float(string='Percentage')
    fixed_amount = fields.Float(string='Amount',
                                digits=(6, 0)
                                )

    def create_rule_salary_deduction(self):
        print('create_rule_salary_deduction')
        for record in self:
            structure_id = record.env['hr.payroll.structure'].search([('id', '=', 2)])
            category_id = record.env['hr.salary.rule.category'].search([('code', '=', 'DED')])
            rule = record.env['hr.salary.rule'].create({
                'name': record.name,
                'category_id': category_id.id,
                # 'struct_id':structure_id.id,
                'code': record.code,
                'active': True,
                'appears_on_payslip': True,
                'amount_select': 'fix',
            })
            deduction = self.env['hr.payslip.deduction.type'].search([('name', '=', rule.name)])
            print('deduction=', deduction)
            print('rule=', rule)
            for allot in deduction:
                if allot.rule_id:
                    allot.rule_id.unlink()  # This will delete the existing rule_id

            for rule_allotment in rule:
                print('rule_allotment=', rule_allotment)
                deduction.write({
                    "rule_id": rule_allotment
                })
