# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PayslipAllotments(models.Model):
    _inherit = 'hr.payslip'

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, readonly=True)
    wage = fields.Monetary("Basic",
                           related='contract_id.wage',
                           readonly=True,
                           store=True,
                           currency_field="currency_id")
    akran_salary = fields.Float("Akran Salary",
                                related='contract_id.akran_salary',
                                readonly=True,
                                store=True)
    marriage_salary = fields.Float("Marriage Salary",
                                   related='contract_id.marriage_salary',
                                   readonly=True,
                                   store=True
                                   )
    net_salary = fields.Float(string='Net salary', digits=(6, 0),
                              readonly=True, compute='_compute__salary_net')  # صافي المرتب
    allotments = fields.Float(string='Allotments', digits=(6, 0), readonly=True)  # المخصصات
    deductions = fields.Float(string='Deductions', digits=(6, 0), store=True,
                              )
    retirement_percentage = fields.Float(string='Retiremnet Percentage')  # نسبة التقاعد
    social_tax = fields.Float(string='Social Security',
                              related='contract_id.social_tax',
                              readonly=True,
                              store=True
                              )
    allotment_ids = fields.One2many(
        string='Allotment',
        comodel_name='hr.payslip.allotment',
        inverse_name='slip_id'
    )
    retirement_amount = fields.Float(string='Retirement Amount',
                                     store=True)
    total_allotments = fields.Float(string='Total', digits=(6, 0), store=True, compute='_compute_total')

    total_deduction = fields.Float(string='Total', digits=(6, 0), store=True, compute='_compute_total_deduction')

    num_of_child = fields.Integer("Children",
                                  related='employee_id.children',
                                  store=True,
                                  readonly=True)

    struct_id = fields.Many2one('hr.payroll.structure', string='Structure',
                                readonly=True)

    rule_ids = fields.One2many('hr.salary.rule', compute='_compute_rule_ids', string='Rules')

    link_rule = fields.One2many('link.rule', 'payslip_id', string="Link Rule", stor=True)
    link_rule_deduction = fields.One2many('link.rule.deduction', 'payslip_id', string="Link Rule Deduction", stor=True)

    @api.onchange('employee_id')
    def get_struct(self):
        for rec in self:
            # Clear existing link_rule records
            rec.link_rule = [(5, 0, 0)]
            if rec.employee_id.contract_id.struct_id:
                rules = rec.employee_id.contract_id.struct_id.rule_ids
                for rule in rules:
                    allotment = self.env['hr.payslip.allotment.type'].search([('rule_id', '=', rule.id)], limit=1)
                    print('allotment=', allotment)
                    print('rule=', rule)
                    if allotment:
                        rec.link_rule = [(0, 0, {'allotment_id': allotment.id})]  # Ensure to use allotment.id
                print('struct=', rules.mapped('name'))

    @api.onchange('employee_id')
    def get_struct_deduction(self):
        for rec in self:
            # Clear existing link_rule records
            rec.link_rule_deduction = [(5, 0, 0)]
            if rec.employee_id.contract_id.struct_id:
                rules = rec.employee_id.contract_id.struct_id.rule_ids
                for rule in rules:
                    deduction = self.env['hr.payslip.deduction.type'].search([('rule_id', '=', rule.id)], limit=1)
                    print('deduction=', deduction)
                    print('rule=', rule)
                    if deduction:
                        rec.link_rule_deduction = [(0, 0, {'deduction_id': deduction.id})]  # Ensure to use allotment.id
                print('struct=', rules.mapped('name'))

    @api.depends('link_rule.total_amount', 'link_rule')
    def _compute_total(self):
        for record in self:
            total = sum(line.total_amount for line in record.link_rule)
            record.total_allotments = total
            record.allotments = total

    @api.depends('link_rule_deduction.total_amount_deduction', 'link_rule_deduction')
    def _compute_total_deduction(self):
        for record in self:
            total = sum(line.total_amount_deduction for line in record.link_rule_deduction)
            record.total_deduction = total
            record.deductions = total

    # @api.depends('retirement_percentage', 'social_tax')
    # def _compute__retirement_ded(self):
    #     for record in self:
    #         wage = record.contract_id.wage
    #         record.retirement_amount = wage * record.retirement_percentage
    #         record.deductions = (wage * record.retirement_percentage) + record.social_tax

    @api.depends('deductions', 'allotments', 'wage')
    def _compute__salary_net(self):
        for record in self:
            record.net_salary = record.allotments + record.wage - record.deductions

    def compute_sheet(self):
        for record in self:
            for rec in record.allotment_ids:
                rec.allotment_id.rule_id.amount_select == 'fix'
                rec.allotment_id.rule_id.amount_fix = rec.total_amount
            # retirement_input_id = self.env['hr.payslip.input.type'].search([('code','=','DEDUCTION')])
            # social_input_id = self.env['hr.payslip.input.type'].search([('code','=','SOCIAL')])
            # record.input_line_ids.unlink()
            # record.input_line_ids.create({
            #     'code': "DED",
            #     'name': 'التقاعد',
            #     'amount': record.retirement_amount,
            #     'payslip_id': record.id,
            #     'contract_id': record.contract_id.id
            # })
            # record.input_line_ids.create({
            #     'code': "SOI",
            #     'name': 'الرعاية الاجتماعية',
            #     'amount': record.social_tax,
            #     'payslip_id': record.id,
            #     'contract_id': record.contract_id.id
            # })
            res = super(PayslipAllotments, record).compute_sheet()
            for rec in record.allotment_ids:
                rec.allotment_id.rule_id.amount_fix = 0
            for line in record.line_ids:
                if line.amount == 0:
                    line.unlink()

            # total = 0
            # for line in record.input_line_ids:
            #     print('Amount=', line.amount)
            #     total += line.amount
            # record.total_deduction = total
            # record.deductions = record.total_deduction

        return res


class LinkRule(models.Model):
    _name = "link.rule"
    _description = "Link Rules "

    payslip_id = fields.Many2one('hr.payslip', string="Payslip", ondelete="cascade")
    allotment_id = fields.Many2one('hr.payslip.allotment.type', string="Allotment", store=True)
    allotment_type = fields.Selection(related='allotment_id.allotment_type')
    code = fields.Char(related='allotment_id.code')
    salary_type = fields.Selection(
        [('basic', 'Basic Salary'), ('akran', 'Akran Salary'), ('marriage', 'Marriage Salary')], default='basic',
        required=True)

    percentage = fields.Float(
        string='Percentage',
        related='allotment_id.percentage',
        readonly=True,
        store=True)
    fixed_amount = fields.Float(
        string='Amount', digits=(6, 0),
        related='allotment_id.fixed_amount',
        readonly=True,
        store=True)
    num = fields.Float(string='Number Of Days', digits=(6, 0))
    total_amount = fields.Float(string='Sub Total', digits=(6, 0),
                                compute='_compute_total_allotment')
    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', compute='_compute_slip', store=True)

    @api.depends('payslip_id')
    def _compute_slip(self):
        for rec in self:
            rec.slip_id = rec.payslip_id

    @api.depends('allotment_id', 'slip_id.allotment_ids', 'allotment_type', 'salary_type', 'fixed_amount', 'percentage')
    def _compute_total_allotment(self):
        for record in self:
            salary = 0
            record.total_amount = 0
            salary = record.slip_id.contract_id.wage if record.slip_id else 0
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
                    record.total_amount = record.fixed_amount * record.slip_id.num_of_child
                elif record.allotment_id.code == 'wife' and record.slip_id.employee_id.marital == 'married':
                    record.total_amount = record.fixed_amount
                else:
                    record.total_amount = record.fixed_amount


class LinkRuleDeduction(models.Model):
    _name = "link.rule.deduction"
    _description = "Link Rules Deduction"

    payslip_id = fields.Many2one('hr.payslip', string="Payslip", ondelete="cascade")
    deduction_id = fields.Many2one('hr.payslip.deduction.type', string="Deduction", store=True)
    deduction_type = fields.Selection(related='deduction_id.deduction_type')
    code = fields.Char(related='deduction_id.code')
    salary_type = fields.Selection(
        [('basic', 'Basic Salary'), ('akran', 'Akran Salary'), ('marriage', 'Marriage Salary')], default='basic',
        required=True)

    percentage = fields.Float(
        string='Percentage',
        related='deduction_id.percentage',
        readonly=True,
        store=True)
    fixed_amount = fields.Float(
        string='Amount', digits=(6, 0),
        related='deduction_id.fixed_amount',
        readonly=True,
        store=True)
    num = fields.Float(string='Number Of Days', digits=(6, 0))
    total_amount_deduction = fields.Float(string='Sub Total', digits=(6, 0),
                                )
    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', store=True)

    # @api.depends('payslip_id')
    # def _compute_slip_deduction(self):
    #     print('_compute_slip_deduction')
    #     # for rec in self:
    #     #     rec.slip_id = rec.payslip_id

    # @api.depends('deduction_id', 'deduction_type', 'salary_type', 'fixed_amount', 'percentage')
    # def _compute_total_deduction(self):
    #     print('_compute_total_deduction')
    #     for record in self:
    #         salary = 0
    #         record.total_amount_deduction = 0
    #         salary = record.slip_id.contract_id.wage if record.slip_id else 0
            # if record.allotment_type == 'percentage':
            #     if record.allotment_id.code == 'cert':
            #         record.percentage = record.slip_id.employee_id.certificate_id.percentage
            #         record.total_amount_deduction = record.percentage * salary
            #     elif record.allotment_id.code == 'title':
            #         record.percentage = record.slip_id.employee_id.job_address_id.percentage
            #         record.total_amount_deduction = record.percentage * salary
            #     else:
            #         record.total_amount_deduction = (record.percentage * salary)

            # if record.allotment_type == 'fixed_amount':
            #     if record.allotment_id.code == 'child':
            #         record.total_amount_deduction = record.fixed_amount * record.slip_id.num_of_child
            #     elif record.allotment_id.code == 'wife' and record.slip_id.employee_id.marital == 'married':
            #         record.total_amount_deduction = record.fixed_amount
            #     else:
            #         record.total_amount_deduction = record.fixed_amount
