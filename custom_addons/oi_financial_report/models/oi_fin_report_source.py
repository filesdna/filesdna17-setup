'''
Created on Sep 28, 2016

@author: Zuhair
'''
from odoo import models, fields,api
import logging
from ..Common import get_sql_date, truncate
from datetime import timedelta, date
from odoo.tools import config

_logger = logging.getLogger(__name__)
_debug = config.get('debug.oi_financial_report')

_Date_Types = [
        ('day','Date'),
        ('week','Week'),
        ('month','Month'),
        ('quarter','Quarter'),
        ('year','Year'),
        ('decade','Decade'),
        ]
_groups= {
            'account' : ('account_account.code', 'account_account.name'),
            'account_type' : ('account_account_type.name', None),
            'analytic' : ('account_analytic_account.code','account_analytic_account.name'),
            'partner' : ("coalesce(res_partner.ref,' ')",'res_partner.name'),
            'country' : ('res_country.code','res_country.name'),
            'product' : ('product_product.default_code','product_template.name'),
            'company' : ('res_company.name',None),
         }

class ReportSource(models.Model):
    
    _name = 'oi_fin.report_source'
    _description = 'oi_fin.report_source'
    _inherit = ['oi_fin.name', 'oi_fin.filter']
    
    description = fields.Char()    
    
    source_type = fields.Selection([
        ('account','Account'),
        ('account_type','Account Type'),
        ('analytic','Analytic Account'),
        ('partner','Partner'),
        ('country','Partner Country'),
        ('product','Product'),
        ('company','Company'),            
        ('other','Other'),            
        ] + _Date_Types, required=False, string='Group By')
    
    is_period_type = fields.Boolean(compute='_calc_period_type', store = True)
    is_mandatory_type = fields.Boolean(compute='_calc_mandatory_type', store = True)
    
    include_empty = fields.Boolean('Include Empty Group', default = True)
    
    period_type = fields.Selection([
            ('period','Period Activity'),
            ('accumulative','Period Activity Accumulative'),
            ('balance','Ending Balance'),], required = True, default='period', string ='Balance Type')        
        
    dimension_id = fields.Many2one('oi_fin.dimension', string='Dimension', domain = [('group_columns', '!=', False)]) 
        
    @api.depends('source_type')
    def _calc_period_type(self):
        period_types = tuple(item[0] for item in _Date_Types)
        for record in self:
            record.is_period_type = record.source_type in period_types
            
    @api.depends('source_type')
    def _calc_mandatory_type(self):
        mandatory_types = tuple(item[0] for item in _Date_Types) + ('account','account_type')
        for record in self:
            record.is_mandatory_type = record.source_type in mandatory_types              
    
    def get_sql(self, budget_move_type = None):
        self.ensure_one()
        res = {}                    
        
        if self.source_type == 'other':
            res['group'] = tuple(self.dimension_id.group_columns.split(','))
            if len(res['group'])==1:
                res['group'] = res['group'] + (None,)
        else:
            res['group'] = _groups.get(self.source_type, (None,None))
            
        if True:
            new_select  = []
            lang = self._context.get('lang', 'en_US')
            for sql_column in res['group']:     
                if sql_column:
                    try:
                        table, column = sql_column.split('.')
                        if table in self.env:
                            model = table
                        else:
                            model = table.replace('_', '.')
                        if model in self.env and column in self.env[model]:
                            field = self.env[model]._fields[column]
                            if field.translate:
                                sql_column = f"translate({sql_column},'{lang}')"
                                                        
                    except ValueError:
                        pass
                new_select.append(sql_column)
            res['group'] = tuple(new_select)
            
        if self._context.get('lang', 'en_US')[:2] == 'ar' and res['group'][0]=="account_account.code" and self.env['ir.config_parameter'].sudo().get_param("oi_financial_report.account_code_arabic","True")=="True":
            gr = list(res['group'])
            gr[0] ="en_to_ar(account_account.code)"
            res['group'] = tuple(gr)            
            
        res['date_format'] = {
            'day' : '%Y-%m-%d',
            'week' : '%Y-%U %b-%d',
            'month' : '%Y-%B',
            'quarter' : lambda value : '%s Q%s' % (value.year,(value.month-1)//3 + 1),
            'year' : '%Y',
            'decade' : '%Y',
            }.get(self.source_type)          
                   
        if _debug:
            _logger.info([self, self.display_name])
            _logger.info(self._context)
                            
        res['where'], res['para'] = self._get_sql_where(budget_move_type = budget_move_type)               
                
        if not self.include_empty and not self.is_mandatory_type:
            where=[]
            for gr in res['group']:                
                if gr:
                    where.append(gr + ' IS NOT NULL')
            if where:
                res['where'].append('(' + ' OR '.join(where) + ')')     
                                
        if _debug:
            _logger.info([self, self.display_name, res['where'], res['para']])                
                                           
        return res
    
    def get_periods(self, start_date, end_date):
        self.ensure_one()
        if not self.is_period_type:
            return [(None,None,None)]
        
        if not start_date:
            start_date = get_sql_date(self, 'select min(account_move.date) from account_move') or date.today()
            
        if not end_date:
            end_date = get_sql_date(self, 'select max(account_move.date) from account_move') or date.today()
            
        source_type=self.source_type
        
        trunc = lambda dt : truncate(dt, source_type)
            
        start_date = trunc(start_date)
        one_day = timedelta(days=1)
        
        def next_period(dt):
            current = trunc(dt)            
            while True:
                dt = dt + one_day
                next_period = trunc(dt)
                if next_period != current:
                    return next_period
                
        last_day = lambda dt : next_period(dt) - one_day                                   
        
        periods = []
        
        period_start_date = start_date
        
        while period_start_date < end_date:
            start = {
                'period': period_start_date,
                'accumulative':start_date,
                'balance' : None
                }[self.period_type]
            end = last_day(period_start_date)
            periods.append((start,end,period_start_date))
            period_start_date = next_period(period_start_date)
                        
        if _debug:
            _logger.info('period %s' % self.name)
            _logger.info(periods)
            
        return periods
            
        
        