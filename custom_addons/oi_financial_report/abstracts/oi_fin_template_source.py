'''
Created on Sep 28, 2016

@author: Zuhair
'''

from odoo import models, fields, api, _
import logging
from odoo.tools import config
from ..Common import SUMMARY_FUNCTIONS
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)
_debug = config.get('debug.oi_financial_report')

class ReportTemplateSource(models.AbstractModel):
    _name = 'oi_fin.template_source'
    _description = 'oi_fin.template_source'
    _order = 'sequence'
    
    sequence = fields.Integer(required = True, default = 1)
        
    report_source_id = fields.Many2one('oi_fin.report_source',required = False, string='Amount Source' )    
    
    name = fields.Char(required = False, translate = True)    
    
    source_type = fields.Selection([('amount','Amount'),
                                    ('title','Title'),
                                    ('calc','Calculation'),
                                    ],
                                   required = True,    
                                   string='Source Type'                                                              
                                   )
    
    calc_type = fields.Selection(SUMMARY_FUNCTIONS + [
                                    ('-','Subtract'), ('/','Divide'),('%','Percentage')
                                    ],
                                   string='Calculation',
                                   default = 'SUM'                                                                    
                                   )
    
    operand_type = fields.Selection([('1','Operand 1'),
                                  ('2','Operand 1 & Operand 2'),
                                    ('3','Range (Operand 1 to Operand 2)'),    
                                    ],
                                   string='Operand Type'                                                                    
                                   )
    
    operand1= fields.Char('Operand 1 Sequence', default = '')
    operand2= fields.Char('Operand 2 Sequence', default = '')
    
    amount_type = fields.Selection([('debit','Debit'),
                                    ('-debit','Debit (-)'),
                                    ('credit','Credit'),
                                    ('-credit','Credit (-)'),
                                    ('balance','Balance (Debit-Credit)'),
                                    ('-balance','Balance (Credit-Debit)'),
                                    ('quantity','Quantity'),
                                    ('amount_residual', 'Residual Amount'),
                                    ('-amount_residual', 'Residual Amount (-)'),
                                    ('balance+','Debit Balance'),
                                    ('-balance+','Credit Balance'),                                    
                                    ],
                                   string='Amount Type',
                                   )  
    
    balance_type = fields.Selection([('begin','Begin Balance'),
                                    ('end','Ending Balance'),
                                    ],
                                   string='Balance Type',
                                   )  
    
    special_filter = fields.Selection([('initial_balance','Begin Balance Auto Adjustment for Expense/Revenue'), 
                                       ('unallocated_earnings', 'Undistributed Profits/Losses'),
                                       ('debit', 'Debit Only'),
                                       ('credit', 'Credit Only')
                                       ], string='Special Filter')
    
    none_zero = fields.Boolean('Include only if has value')
    
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')    
        
    hidden = fields.Boolean()
    
    @api.constrains('sequence')
    def sequence_check(self):
        for record in self:
            if record.sequence == 0:
                raise UserError('Sequence = 0')
    
    @api.onchange('report_source_id')
    def on_report_source_change(self):
        for record in self:
            if not record.name and record.report_source_id:
                record.name = record.report_source_id.name
                                      
    @api.constrains('date_from', 'date_to')
    def _check_date(self):
        for record in self:
            if record.date_from and record.date_to and  record.date_from > record.date_to:
                raise ValidationError(_('Start Date > End Date'))      
            
    
    @api.constrains('name')
    def _check_name(self):
        for record in self:
            if not record.name:
                record.name = ' '
            
    
    def name_get(self):
        res = []
        for record in self:
            res.append((record.id, "%s %s" % (record.sequence, record.name)))
        return res
