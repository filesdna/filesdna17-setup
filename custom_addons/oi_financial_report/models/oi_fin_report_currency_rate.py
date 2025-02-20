'''
Created on Sep 19, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields

class ReportCurrencyRates(models.TransientModel):    
    _name = 'oi_fin.report.currency_rate'
    _description = _name    
    
    report_id = fields.Many2one('oi_fin.report', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', required = True)
    rate = fields.Float(digits=(12, 6))
    
    _sql_constraints = [
        ('currency_uk', 'unique(report_id, currency_id)', 'Currency must be unique!')
        ]    
    