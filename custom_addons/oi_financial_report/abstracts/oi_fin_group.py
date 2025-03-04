'''
Created on Oct 27, 2016

@author: Zuhair
'''

from odoo import models, fields
import logging
from odoo.tools import config


_logger = logging.getLogger(__name__)
_debug = config.get('debug.oi_financial_report')

class Group(models.AbstractModel):
    
    _name = 'oi_fin.group'
    _description = 'oi_fin.group'
    _inherit = 'oi_fin.filter'
    
    group_by = fields.Selection([
                                ('company','Company'),
                                ('partner','Partner'),
                                 ('account','Account'),
                                 ('analytic','Analytic Account'),
                                 ('journal','Journal'),
                                 ('product','Product'),
                                 ('country','Partner Country'),
                                 ('account_type','Account Type'),
                                 ('account_group','Account Group'),
                                 ('other','Other')
                                 ],
                                'Group By',                                
                                )
    
    include_empty = fields.Boolean('Include Empty Group', default = True)       
    dimension_id = fields.Many2one('oi_fin.dimension', string='Dimension', domain = [('group_columns', '!=', False)])
          
    def get_parameter_info(self):
        rows = []
        
        def fields_tocopy(f):
            if self._fields[f].automatic:
                return False
            return True
                
        _fields = (field_name for field_name in filter(fields_tocopy, self.env['oi_fin.group']._fields))  
        _fields = sorted((self._fields[f].string or f,f) for f in _fields)
        for name,key in _fields:
            value =getattr(self, key)
            
            if self._fields[key].compute:
                continue
            
            if self._fields[key].type =='selection':
                for key, item in self._fields[key].selection:
                    if key==value:
                        value = item
                        break
            
            def get_obj_info(record):
                info=[]
                info.append(getattr(record, 'code',None))
                info.append(getattr(record, 'ref',None))
                info.append(getattr(record, 'name',None))
                return filter(None,info)
            
            if isinstance(value, models.BaseModel):
                if len(value)>1:
                    rows.append([name])
                    for record in value:
                        rows.append([''] + get_obj_info(record))
                else:
                    rows.append([name] + get_obj_info(value))
            else:
                rows.append([name, value])
                
        if _debug:
            _logger.info(rows)
                
        return rows
    
    def get_groups(self, begin_balance = False):
        cr = self.env.cr
        if not self.group_by:
            return (None,),None
                    
        select = {
            'company' : ('res_company.id', 'res_company.name'),
            'partner' : ('res_partner.id', 'res_partner.ref', 'res_partner.name'),
            'account' : ('account_account.id', 'account_account.code', 'account_account.name'),
            'analytic' : ('account_analytic_account.id', 'account_analytic_account.code', 'account_analytic_account.name'),
            'journal': ('account_journal.id','account_journal.code','account_journal.name'),
            'product': ('product_product.id','product_product.default_code','product_template.name'),
            'country': ('res_country.id','res_country.code','res_country.name'),
            'account_type': ('account_type.id','account_type.name'),
            'account_group': ('account_group.id','account_group.code_prefix','account_group.name'),
            'other' : lambda self : tuple(self.dimension_id.group_columns.split(','))
            }[self.group_by]
                    
        if callable(select):
            select = select(self)             
            if len(select) == 1:
                select = select + select

        if True:
            new_select  = []
            lang = self._context.get('lang', 'en_US') 
            for sql_column in select:                
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
            select = tuple(new_select)
            
        if self._context.get('lang', 'en_US')[:2] == 'ar' and self.group_by =='account' and self.env['ir.config_parameter'].sudo().get_param("oi_financial_report.account_code_arabic","True")=="True":
            new_select  = []
            for sql_column in select:       
                if sql_column == 'account_account.code':
                    sql_column = "en_to_ar(account_account.code)"
                new_select.append(sql_column)
            select = tuple(new_select)
                    
        group_filter = select[0]
        if begin_balance:
            begin_balances = [True, False]
        else:
            begin_balances = [False]
        
        groups = []
        for begin_balance in begin_balances:
            where , para = self._get_sql_where(begin_balance = begin_balance)
            if not self.include_empty:
                where.append(group_filter + ' IS NOT NULL')      
            self._add_company_filter(where,para)
            sql = [] 
            sql.append('SELECT distinct ')
            sql.append(",\n".join(select))
            sql.append(self.env['oi_fin.report']._get_sql_from(analytic = self.group_by == 'analytic'))             
            if where: 
                sql.append('WHERE ')
                sql.append("\nAND ".join(where))
            sql.append(' ORDER BY ')
            sql.append(','.join(select[1:]))
            sql = "\n".join(sql)
            if _debug:
                _logger.info(sql)
                _logger.info(para)
            cr.execute(sql, para)
            groups.extend(cr.fetchall())
        
        groups = sorted(set(groups), key = lambda item : tuple(map(lambda i: (1 if i is None else 0, i) ,item[1:])))  
        if _debug:
            _logger.info(groups)
        return (groups, group_filter)   