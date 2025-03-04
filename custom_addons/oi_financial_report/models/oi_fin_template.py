'''
Created on Sep 19, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval

class ReportTemplate(models.Model):
    
    _name = 'oi_fin.template'
    _description = 'oi_fin.template'
    _inherit = ['oi_fin.name', 'oi_fin.group','oi_fin.summary','oi_fin.menu']
    _template_col = 'report_template'
    _transient_model = 'oi_fin.report'
    _transient = False
    _abstract = False    
        
    columns = fields.One2many('oi_fin.template_column','report_template', required = True, copy = True)
    rows = fields.One2many('oi_fin.template_row','report_template', required = True, copy = True)
    sample = fields.Boolean(copy = False)
        
    active = fields.Boolean(default = True)
    
    cash_basis = fields.Boolean('Cash Basis')

    columns_count = fields.Integer(compute = '_calc_columns_count')
    rows_count = fields.Integer(compute = '_calc_rows_count')
    
    report_id = fields.Many2one('ir.actions.report', string='QWeb Report', domain = [('model', '=', 'oi_fin.report')], default = lambda self : self.env.ref('oi_financial_report.act_report_oi_fin_report', False))
    
    show_transaction = fields.Boolean('Show Transaction Details')
    
    @api.depends('columns')
    def _calc_columns_count(self):
        for record in self:
            record.columns_count = len(record.columns)
            
    @api.depends('rows')
    def _calc_rows_count(self):
        for record in self:
            record.rows_count = len(record.rows)            
                
    
    def action_view_columns(self):
        action, = self.env.ref("oi_financial_report.act_oi_fin_template_column").read()
        action['domain'] = [('report_template', '=', self.id)]
        action['context'] = {
            'default_report_template' : self.id
            }
        return action
    
    
    def action_view_rows(self):
        action, = self.env.ref("oi_financial_report.act_oi_fin_template_row").read()
        action['domain'] = [('report_template', '=', self.id)]
        action['context'] = {
            'default_report_template' : self.id
            }
        return action    
    
    
    def action_run_report(self):
        action, = self.env.ref("oi_financial_report.act_oi_fin_report").read()
        action['target'] = 'current'
        action['context'] = safe_eval(action.get('context') or '{}')
        action['context'].update({
            'default_report_template' : self.id,
            'form_view_hide_buttons_edit' : True
            })
        return action         