'''
Created on Sep 19, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields
from ..Common import SUMMARY_FUNCTIONS

class ReportSummary(models.AbstractModel):
    
    _name = 'oi_fin.summary'     
    _description = 'oi_fin.summary'     
    
    add_summary_row = fields.Boolean('Add Summary Row')
    summary_row_func = fields.Selection(SUMMARY_FUNCTIONS, default = 'SUM')    
    
    add_summary_column = fields.Boolean('Add Summary Column')
    summary_column_func = fields.Selection(SUMMARY_FUNCTIONS, default = 'SUM')
