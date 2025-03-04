# -*- coding: utf-8 -*-

from odoo import models, fields, api
from lxml import etree


class EmployeeMoreDetails(models.Model):
    _inherit = 'hr.employee'

    employee_num  = fields.Char("Employee Number",
     )
    religion = fields.Selection(string='Religion', selection=[
        ('islam', 'Islam'), ('christianity', 'Christianity'),
        ('jew', 'Jewish')
        ],default='islam',required=True)
    grade = fields.Many2one(comodel_name='hr.employee.grade', string='Grade') #الدرجة 
    level = fields.Many2one(comodel_name='hr.employee.level', string='Level') #المرحلة
    specialization = fields.Many2one(comodel_name='hr.employee.specialization', string='Specialization') #التخصص
    transfer_from = fields.Char(string='Transfer From',
     ) #الجهة منقول منها
    transfer_to = fields.Char(string='Transfer To',
     ) # الجهة منقول اليها
    mother_name = fields.Char(string='Mother Full Name',
     ) #اسم الام
    mother_s_name = fields.Char(string='Second Name',
     ) #اسم الام
    mother_t_name = fields.Char(string='Third Name',
     ) #اسم الام
    goverment_number = fields.Char(string='Government Number') #الرقم الحكومي
    # /////////////// Civilian ID INfo//////////////////////////////////////
    civilian_id = fields.Char(string='Civilian ID') 
    civilian_record_number = fields.Char(string='Civilian record number') 
    civilian_page_number = fields.Char(string='Civilian Page Number') 
    civilian_issue_date = fields.Date('Issue Date')
    civilian_expire_date = fields.Date('Expire Date')
    civilian_governorate_id = fields.Many2one('hr.employee.governorate', string='State')
    # /////////////////////////////////////////////////////////////////////////
    pass_issue_date = fields.Date('Issue Date')
    pass_expire_date = fields.Date('Expire Date')
    pass_governorate_id = fields.Many2one('hr.employee.governorate', string='State')
    # ///////////////////////////// Notional ID ////////////////////////////////////////////////////////
    national_id = fields.Char(string='National ID') 
    national_issue_date = fields.Date('Issue Date')
    national_expire_date = fields.Date('Expire Date')
    national_governorate_id = fields.Many2one('hr.employee.governorate', string='State')
    # //////////////////////////////////////////////////////////////////////////////////////////////
    previous_marriage_state  = fields.Selection([
    ('single', 'Single'),
    ('married','Married'),
    ('cohabitant','Cohabitant'),
    ('widower','Widower'),
    ('divorced','Divorced')
    ],default='single',string='Previous Marriage Status') # حالة الزواج السابقة

    service_status = fields.Selection([
        ('fired', 'Fired'),('on_service', 'On Service'),
        ('retired', 'Retired'),('transferd', 'Transferd'),
        ('died', 'Died'),('quit', 'Quit'),
        ('loaned', 'Loaned'),('out_service', 'Out of Service'),
        ('removed', 'Removed')
        ])
    certificate_id=  fields.Many2one(
        comodel_name='hr.employee.certifiaction',
        string='Certification'
        )
    contact_id  = fields.Many2one(
        comodel_name='hr.employee.contact',
        string='Contact Relation'
        )
    job_address_id = fields.Many2one('job.address', string='Job Title')
    governorate_id = fields.Many2one('hr.employee.governorate', string='State')
    
    residence_card = fields.Char('Residence Card')
    residence_card_office = fields.Char('Residence Card Office Info',)
    residence_card_governorate_id = fields.Many2one('hr.employee.governorate', string='State')
    locked = fields.Boolean('',default=False)
    
    def locked(self):
        for record in self:
            record.locked = True

    
   
class HrEmployeeGrade(models.Model):

    _name = 'hr.employee.grade'
    _description = 'Employees Grades'

    name = fields.Char(string='Name')
    code = fields.Integer(string='Code')

class HrEmployeeLevel(models.Model):

    _name = 'hr.employee.level'
    _description = 'Employees levels'

    name = fields.Char(string='Name' , 
     
    )

class HrEmployeeSpecialization(models.Model):

    _name = 'hr.employee.specialization'
    _description = 'Employees specializations'

    name = fields.Char(string='Name' , 
     
    )

class EmployeeContactRelation(models.Model):

    _name = 'hr.employee.contact'

    name  = fields.Char(string='Relation',
     )
    
class EmployeeState(models.Model):

    _name = 'hr.employee.governorate'

    name  = fields.Char(string='Governorate(State)',
     )

class EmployeeState(models.Model):

    _name = 'hr.employee.certifiaction'

    name  = fields.Char(string='Certification',)
    percentage = fields.Float(string='Percentage')


