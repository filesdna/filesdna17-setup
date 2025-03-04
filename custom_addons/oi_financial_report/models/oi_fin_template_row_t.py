'''
Created on Sep 19, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields

class ReportTemplateRowT(models.TransientModel):
    _name = 'oi_fin.template_row_t'
    _description = 'oi_fin.template_row_t'
    _inherit = ['oi_fin.template_source']   
    
    report = fields.Many2one('oi_fin.report',required = True, ondelete='cascade')
    report_template = fields.Many2one(related='report', string="Report Wizard")