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
    store=True    )
    marriage_salary = fields.Float("Marriage Salary",
    related='contract_id.marriage_salary',
    readonly=True,
    store=True
    )
    net_salary  = fields.Float(string='Net salary',  digits=(6, 0),
    readonly=True,compute='_compute__salary_net') #صافي المرتب
    allotments = fields.Float(string='Allotments',  digits=(6, 0),readonly=True) #المخصصات
    deductions = fields.Float(string='Deductions',  digits=(6, 0),store=True,
     compute='_compute__retirement_ded') 
    retirement_percentage = fields.Float(string='Retiremnet Percentage') #نسبة التقاعد 
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
    retirement_amount = fields.Float(string='Retirement Amount',compute='_compute__retirement_ded',
    store = True )
    total_allotments= fields.Float(string='Total',  digits=(6, 0),store=True,compute='_compute_total')


    num_of_child =  fields.Integer("Children",
    related='employee_id.children',
    store = True,
    readonly=True)


    @api.depends('allotment_ids.total_amount','allotment_ids')
    def _compute_total(self):
        for record in self:
            total = 0
            for line in record.allotment_ids:
                total += line.total_amount
            record.total_allotments = total
            record.allotments = total
            
    @api.depends('retirement_percentage','social_tax')
    def _compute__retirement_ded(self):
        for record in self:
            wage = record.contract_id.wage
            record.retirement_amount = wage * record.retirement_percentage
            record.deductions = (wage * record.retirement_percentage) + record.social_tax

    @api.depends('deductions','allotments','wage')
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
            record.input_line_ids.unlink()
            record.input_line_ids.create({
                'code':"DED",
                'name':'التقاعد',
                'amount':record.retirement_amount,
                'payslip_id':record.id,
                 'contract_id':record.contract_id.id
            })
            record.input_line_ids.create({
                'code':"SOI",
                'name':'الرعاية الاجتماعية',
                'amount':record.social_tax,
                'payslip_id':record.id,
                'contract_id':record.contract_id.id
            })
            res=super(PayslipAllotments, record).compute_sheet()
            for rec in record.allotment_ids:
                rec.allotment_id.rule_id.amount_fix = 0
            for line in record.line_ids:
                if line.amount == 0:
                    line.unlink()
            
        return res
