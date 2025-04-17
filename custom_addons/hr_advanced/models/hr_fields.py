# -*- coding: utf-8 -*-

from odoo import models, fields, api



class EmployeeMoreDetails(models.Model):

    _inherit = 'hr.employee'



    postion_date = fields.Date(string='Date of position')
    postion_num = fields.Char(string='Postion Order Number')

    bouns_amount  = fields.Integer(string='Bouns Amount')
    bouns_due_date  = fields.Date(string='Bouns Due Date')
    bouns_last_date  = fields.Date(string='Last Bouns Date')

    hiring_date = fields.Date(string='Hiring Date')
    hiring_order = fields.Date(string='Hiring Order Date')
    hiring_order_num = fields.Char(string='Hiring Order Number')
    
    Joining_date = fields.Date(string='Joining Date')
    joing_order_number = fields.Char(string='Joining Order Number')
    joing_order_date = fields.Date(string='Joining Order Date')
    
    add_service_yearly= fields.Integer(string='Yearly Addtional Service')
    add_service_monthly= fields.Integer(string='Monthly Addtional Service')
    add_service_daily= fields.Integer(string='Daily Addtional Service')

    removed_service_yearly= fields.Integer('Yearly Removed Service')
    removed_service_monthly= fields.Integer('Monthly Removed Service')
    removed_service_daily= fields.Integer('Daily Removed Service')

    service_note = fields.Char(string='Service Note')

    management_Situation = fields.Integer(string='Management Situation')
    employment_status = fields.Char(string='Employment status')
    employment_status_date= fields.Date(string='Employment Status Date')
    employment_status_number = fields.Char(string='Employment status Number')
    resign_date = fields.Date(string='Resign Date')

    service_law  = fields.Char(string='Service Law')
    loan_department_id = fields.Many2one('hr.department', string='Department representative')

    first_cert = fields.Integer(string='First Certification')
    second_cert = fields.Integer(string='Second Certification')
    third_cert = fields.Integer(string='third Certification')

    universtiy  = fields.Char("Universtiy")
    graduate_year = fields.Date(string='Graduate Year')
    language  = fields.Many2many('hr.employee.language', string='Language')

    partner_job = fields.Char(string='Partner Job')
    partner_nationlity  = fields.Many2one('res.country', string='Partner nationality')
    marriage_allotment  = fields.Integer()

    supply_card  = fields.Char("Supply Card")
    supply_card_center  = fields.Char("Supply Card Center")




class Employeelanguage(models.Model):

    _name = 'hr.employee.language'
    _description = ''

    name  = fields.Char('Name')

    