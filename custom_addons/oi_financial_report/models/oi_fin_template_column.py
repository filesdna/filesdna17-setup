'''
Created on Sep 19, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields

class ReportTemplateColumn(models.Model):
    _name = 'oi_fin.template_column'
    _description = 'oi_fin.template_column'
    _inherit = ['oi_fin.template_source']
    
    report_template = fields.Many2one('oi_fin.template',required = True, ondelete='cascade')
