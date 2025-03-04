'''
Created on Sep 28, 2016

@author: Zuhair
'''
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import config
import logging
from ..Common import SQL_FROM, SQL_FROM_BUDGET, string_types
from datetime import date
from docutils.nodes import field_name
from xlsxwriter.utility import xl_col_to_name
import json
import odoo
from dateutil.relativedelta import relativedelta
import itertools
from openpyxl.styles import Alignment

_MAX_INT = 1024*1024

_logger = logging.getLogger(__name__)
_debug = config.get('debug.oi_financial_report')

class Report(models.TransientModel):
    
    _name = 'oi_fin.report'
    _description = 'oi_fin.report'
    
    _inherit = ['oi_fin.group', 'oi_fin.summary']
    
    columns = fields.One2many('oi_fin.template_column_t','report', required = True)
    rows = fields.One2many('oi_fin.template_row_t','report', required = True)
    name = fields.Char()
    report_template = fields.Many2one('oi_fin.template', string='Report Template',required=False, ondelete='cascade')
        
    cash_basis = fields.Boolean('Cash Basis')
    
    currency_id = fields.Many2one('res.currency', required = True, default = lambda self : self.env.company.currency_id)
    currency_rate_date = fields.Date(required = True, default = fields.Date.today)
    currency_rate_ids = fields.One2many('oi_fin.report.currency_rate', 'report_id')
    
    active = fields.Boolean(default = True)
    
    report_id = fields.Many2one('ir.actions.report', string='QWeb Report', domain = [('model', '=', 'oi_fin.report')], default = lambda self : self.env.ref('oi_financial_report.act_report_oi_fin_report', False))
    
    show_transaction = fields.Boolean('Show Transaction Details')    
    transaction_date = fields.Date()
    
    data = fields.Text()
    
    company_ids = fields.Many2many(default = lambda self: self.env.companies)
    
    is_analytic = fields.Boolean(compute = '_calc_is_analytic')
    
    def _calc_is_analytic(self):
        for record in self:
            is_analytic = record.group_by == 'analytic'
            
            for item in itertools.chain(record.rows, record.columns):
                if item.report_source_id.source_type == 'analytic':
                    is_analytic = True
                    break
            
            record.is_analytic = is_analytic            
    
    @api.onchange('date_from', 'date_to')
    def _onchange_set_transaction_date(self):
        date = self.date_from or self.date_to or fields.Date.today()
        self.transaction_date = date.replace(day = 1, month = 1)
            
    @api.onchange('currency_id', 'currency_rate_date')
    def _onchange_currency_id(self):
        self.currency_rate_ids = False
        for currency_id in self.env['res.currency'].search([]):    
            vals =   {
                    'currency_id' : currency_id.id,
                    'rate' : self.env['res.currency']._get_conversion_rate(currency_id, self.currency_id, self.env.company, self.currency_rate_date)
                    }
            if isinstance(self.id, models.NewId):      
                self.currency_rate_ids += self.currency_rate_ids.new(vals)
            else:
                self.write({'currency_rate_ids' : [(0,0,vals)]})                            
        
    @api.onchange('report_template')
    def _on_report_template_change(self):        
        if self.report_template:
            company_ids = self.company_ids
            self.copy_template(self.report_template, self)
            if company_ids and not self.company_ids:
                self.company_ids = company_ids
                                            
    def copy_template(self, obj_from, obj_to):
        data, = obj_from.copy_data()
        for field_name in ('date_from', 'date_to','target_move'):
            data.pop(field_name, False)
        for field_name in list(data.keys()):
            if field_name not in obj_to._fields:
                data.pop(field_name, False)
        obj_to.rows = False
        obj_to.columns = False
        for fname in ['rows', 'columns']:
            if fname in data:
                data[fname] = sorted(data[fname], key = lambda item : item[2]['sequence'])
        obj_to.update(data)            
            
    def create_template(self):
        self.ensure_one()
        if not self.name:
            raise UserError('Enter Name')
        tmpl = self.env['oi_fin.template']
        if tmpl.search_count([('name','=', self.name)]):
            raise UserError('Name already exists')
        tmpl = tmpl.create(dict(name=self.name))
        self.copy_template(self, tmpl)
        self.report_template = tmpl            
        
        return {
            'type' : 'ir.actions.client',
            'tag' : 'display_notification',
            'params': {
                'type': 'info',
                'message': _('Template Created (%s)') % self.name,
                'next': {'type': 'ir.actions.act_window_close'},
            }            
        }
                                                                   
            
    def _get_sql_from(self, budget_move_type = None, analytic = False):
        sql = budget_move_type and SQL_FROM_BUDGET or SQL_FROM
        if self.currency_rate_ids:
            sql += """
INNER JOIN oi_fin_report_currency_rate ON (oi_fin_report_currency_rate.currency_id = res_company.currency_id and oi_fin_report_currency_rate.report_id = %d)            
            """ % self.id
        for dimension in self.env['oi_fin.dimension'].search([('sql_from','!=', False)]):
            sql += '\n' + dimension.sql_from
            
        if analytic or self.is_analytic:
            sql +="""
LEFT JOIN account_analytic_account ON (account_move_line.analytic_distribution->account_analytic_account.id::text is not null)            
LEFT JOIN account_analytic_plan ON (account_analytic_account.plan_id = account_analytic_plan.id)
            """
                                                
        return sql
    
    def _fix_sql(self, sql):
        return sql.replace('amount_residual', 'account_move_line.amount_residual')
    
    
    def clear_form(self):
        default = self.default_get(list(self._fields))
        for name, field in self._fields.items():
            if field.automatic:
                continue
            elif name in default:
                self[name]= default.get(name)            
            elif field.type in ['one2many', 'many2many']:
                self.write({name : [(5,)]})
            elif not field.required:
                self[name] = False
        self._onchange_currency_id()
        self._on_report_template_change()
        return {
            'type' : 'ir.actions.client',
            'tag' : 'trigger_reload',
            }
        
        
    def _openpyxl_func(self, wb, ws, set_attr, html = False):
        ws.sheet_properties.pageSetUpPr.fitToPage = True 
                                         
        if html:
            normal = wb._named_styles['Normal']
            normal.font.size = 15               
        

    def run_report(self):
        year_start = False
        if self.date_from:
            company_ids = self.company_ids or self.env.company
            year_start = 'account.fiscal.year' in self.env and self.env['account.fiscal.year'].search([('company_id','in', company_ids.ids), ('date_from','<=', self.date_from), ('date_to','>=', self.date_from)], limit = 1).date_from \
                or (self.date_from + relativedelta(day = 1, month = 1))
        
        
        self = self.with_context(date_from = self.date_from, date_to = self.date_to, report = self, year_start = year_start)                
        
        if _debug:
            _logger.info('run_report')
            _logger.info(self._context)
        self.ensure_one()        
        
        decimal_places=self.currency_id.decimal_places
        
        self.env['account.move'].check_access_rights('read')
        
        pdf = self._context.get('pdf', False)
        html = self._context.get('html', False)
        
        if not self.rows and not self.columns:
            raise UserError('Select rows and columns')
        
        cr = self.env.cr
        data =[]
        parameter = False
        
        date_from = self.date_from and fields.Date.from_string(self.date_from)
        date_to = self.date_to and fields.Date.from_string(self.date_to)            
                
        def get_min(*args):
            ls = list(filter(None, args))
            return ls and min(ls) or None
            
        def get_max(*args):
            ls = list(filter(None, args))
            return ls and max(ls) or None 
        
        def get_first(*args):
            for a in args:
                if a : return a 
                        
                  
        row_headers =[]
        column_headers=[]
        empty_row_headers =[]
        empty_column_headers=[]
        column_title_seq = set()
        row_title_seq = set()        
        
        data_source_sql = {}
        
        groups_res, group_filter = self.get_groups()
        for group_index,group_res in enumerate(groups_res):        
            if group_res:
                row_headers.append(((group_index, None),group_res[1],group_res[2:3], ", ".join(group_res[3:])))
                row_headers.append(((group_index, _MAX_INT),None,None, None))
            for column in self.columns:         
                budget_move_type = False       
                if 'budget_move_type' in column:
                    budget_move_type = column.budget_move_type
                if column.source_type == 'title':
                    column_headers.append(((1, column.sequence),column.name,None, None))
                    column_title_seq.add(column.sequence)
                    continue
                elif column.source_type == 'calc':
                    column_headers.append(((1, column.sequence),column.name,(column.calc_type,column.operand_type, column.operand1, column.operand2), None))
                    continue                
                column_periods =  column.report_source_id.get_periods(date_from, date_to)
                column_res = column.report_source_id.get_sql(budget_move_type = budget_move_type)
                if _debug:
                    _logger.info([column.display_name, 'column_res', column_res])
                #column_where , column_para = column.report_source_id._get_sql_where(res = column_res)
                column_where , column_para = column_res['where'], column_res['para']
                if _debug:
                    _logger.info([column.display_name, 'column_where , column_para', ' AND '.join(column_where) % tuple(column_para)])                
                for column_period in column_periods:                                                 
                    for row in self.rows:                        
                        if not budget_move_type and 'budget_move_type' in row:
                            budget_move_type = row.budget_move_type
                        
                        row = row.with_context(balance_type = row.balance_type)
                        if row.source_type == 'title':
                            title = row.name
                            if title == '_':
                                title = ' '
                            row_headers.append(((group_index, row.sequence),title,None, None))
                            row_title_seq.add(row.sequence)
                            continue
                        elif row.source_type == 'calc':
                            row_headers.append(((group_index, row.sequence),row.name,(row.calc_type,row.operand_type, row.operand1, row.operand2), None))
                            continue                        
                        row_periods =  row.report_source_id.get_periods(date_from, date_to)
                        row_res = row.report_source_id.get_sql(budget_move_type = budget_move_type)
                        row_where, row_para = row.report_source_id._get_sql_where(res = row_res, budget_move_type=budget_move_type)
                        balance_type = column.balance_type or row.balance_type 
                        for row_period in row_periods:
                            v_date_from = get_max(date_from, column_period[0], row_period[0])
                            v_date_to = get_min(date_to, column_period[1], row_period[1])             
                            case = []                 
                            where, para = self._get_sql_where(where = column_where+ row_where ,
                                                               para = column_para + row_para ,
                                                               date_from =v_date_from,
                                                               date_to=v_date_to,
                                                               balance_type = balance_type,
                                                               row =row ,
                                                               column = column,
                                                               case = case,
                                                               budget_move_type = budget_move_type )        
                            for item in [row, column]:
                                if item.date_from:
                                    where.append('account_move.date >= %s')
                                    para.append(item.date_from)     
                                if item.date_to:
                                    where.append('account_move.date <= %s')
                                    para.append(item.date_to)                                       
                                                                                                      
                            if group_filter:
                                if group_res[0]:
                                    where.append(group_filter + ' = %s')
                                    para.append(group_res[0])
                                else:
                                    where.append(group_filter + ' IS NULL')
                            self._add_company_filter(where,para)                
                            
                            groups =[]
                            groups.extend(column_res['group'])
                            groups.extend(row_res['group'])
                            groups_select = tuple(gr if gr else 'null' for gr in groups)
                            groups_by = tuple(gr for gr in groups if gr)
                            select =[]                
                            select.extend(groups_select)
                            column_sql = get_first(column.amount_type,row.amount_type,'balance')                            
                            
                            positive_only = False
                            if column_sql.endswith('+'):
                                positive_only = True
                                column_sql = column_sql[:-1]                            
                                                            
                            
                            if budget_move_type:
                                budget_column_sql = {
                                    'debit' : 'case when amount <0 then -amount else 0 end',
                                    '-debit' : 'case when amount <0 then amount else 0 end',
                                    'credit' : 'case when amount >0 then amount else 0 end',
                                    '-credit' : 'case when amount >0 then -amount else 0 end',
                                    'balance' : 'amount',
                                    '-balance' : '-amount',
                                    }.get(column_sql)
                                if not budget_column_sql:
                                    raise ValidationError('Invalid Amount Type (%s) for budget' % column_sql )
                                column_sql = budget_column_sql
                                                            
                            if self.cash_basis and not budget_move_type:
                                for v in ['debit', 'credit', 'balance']:
                                    column_sql = column_sql.replace(v, '%s_cash_basis' % v)
                            if case:
                                column_sql = case[0] % column_sql
                                
                            if self.is_analytic:
                                column_sql = f"{column_sql} * (account_move_line.analytic_distribution->account_analytic_account.id::text)::numeric / 100"
                                
                            if self.currency_rate_ids:
                                column_sql = "(%s) * oi_fin_report_currency_rate.rate" % column_sql
                                
                            if positive_only:
                                select.append('round(case when coalesce(sum(%s),0) >0 then coalesce(sum(%s),0) else 0 end, %d)' % (column_sql, column_sql, decimal_places))                                
                            else:
                                select.append('round(coalesce(sum(%s),0), %d)' % (column_sql, decimal_places))                                
                            
                            sql = ['SELECT']
                            sql.append(','.join(select))
                            sql.append(self._get_sql_from(budget_move_type))
                            if where:
                                sql.append('WHERE')
                                sql.append('\nAND '.join(where))
                            if groups_by:
                                sql.append('GROUP BY')
                                sql.append(','.join(groups_by))
                            sql = '\n'.join(sql)
                            if _debug:
                                _logger.info(sql % tuple(para))         
                            sql = self._fix_sql(sql)                       
                            cr.execute(sql, para)
                            records = []
                            
                            def set_dateformat(date_format, *arg):                        
                                if date_format:
                                    res = []
                                    for a in arg:
                                        value = a
                                        if isinstance(a, date):
                                            if callable(date_format):
                                                value = (a,date_format(a))
                                            elif isinstance(date_format, string_types):
                                                value = (a,a.strftime(date_format))
                                        res.append(value)                              
                                    return res
                                return arg    
                            
                            fetch_result = cr.fetchall()
                            if not fetch_result and not row.none_zero and not column.none_zero:
                                fetch_result = [(None, None, None, None, None)]                 
                                                                   
                            for record1 in fetch_result:
                                if (row.none_zero or column.none_zero) and not record1[4]:
                                    continue
                                record2 =[]
                                column_header = [(1, column.sequence, column_period[2], column.id), column.name,record1[0],record1[1] or column_period[2]]
                                row_header = [(group_index,row.sequence), row.name,record1[2] or '',record1[3] or row_period[2] or '']                                
                                        
                                column_header[2:4]=set_dateformat(column_res['date_format'], *column_header[2:4])
                                row_header[2:4]=set_dateformat(row_res['date_format'], *row_header[2:4])
                                    
                                record2.append(tuple(column_header))
                                record2.append(tuple(row_header))
                                record2.append(record1[4])
                                record2 = tuple(record2)
                                
                                data_source_sql[record2] = {
                                    'column_sql' : column_sql,
                                    'where' : where,
                                    'para' : para,
                                    'groups_by' : groups_select,
                                    'record1' : record1,
                                    'budget_move_type' : budget_move_type
                                    }
                                
                                records.append(record2)   
                            if not records and not row.none_zero and not column.none_zero:                                
                                column_header = [(1, column.sequence),column.name,None,column_period[2]]
                                row_header = [(group_index,row.sequence), row.name,'  ', row_period[2]]
                                column_header[2:4]=set_dateformat(column_res['date_format'], *column_header[2:4])
                                row_header[2:4]=set_dateformat(row_res['date_format'], *row_header[2:4])
                                column_header = tuple(column_header)
                                row_header = tuple(row_header)
                                empty_column_headers.append(column_header)
                                empty_row_headers.append(row_header)
                                if len(self.columns)==1:
                                    record2 =[]
                                    record2.append(tuple(column_header))
                                    record2.append(tuple(row_header))
                                    record2.append(0.0)
                                    records.append(record2)
                                #print 'e',record2
                            if _debug:
                                _logger.info('%s %s records' % (row.name, column.name))
                                for index,record in enumerate(records):
                                    _logger.info('[%s] %s' % (index, record))   
                            data.extend(records)
                            
        
        group_length = 3
                
        column_headers = set(column_headers + [record[0] for record in data])
        row_headers = set(row_headers + [record[1] for record in data])
        
        for e_col in empty_column_headers:
            found = False
            for col in column_headers:
                if col[0] == e_col[0]:
                    found = True
                    break
            if not found:
                column_headers.add(e_col)
                
        for e_row in empty_row_headers:
            found = False
            for row in row_headers:
                if row[0] == e_row[0]:
                    found = True
                    break
            if not found:
                row_headers.add(e_row)                
        
        
        def _key(value):
            if isinstance(value, tuple):
                if len(value)==0:
                    return ''
                res = []
                for item in value:
                    res.append(_key(item))
                return tuple(res)
            if value is None:
                return ''
            if isinstance(value, int):
                return '%010d' % value
            return str(value)
                                        
        column_headers = sorted(column_headers, key = _key)
        row_headers= sorted(row_headers, key = _key)
                  
        rows = [None] * (len(row_headers) + group_length)
        
        group_rows =[]    
        total_rows = []   
        summary_rows = []       
        empty_rows = []
        title_rows = []
        percentage_columns = []
        percentage_rows= []
        outlines_row = set()        
        collapse_row = set()
        
        hidden_rows = []
        hidden_columns = []
        
        data_source = []
        data_source_cell = []
                
        for row_index, row_header in enumerate(row_headers):            
            if not row_header[0][1]:
                group_rows.append(row_index + group_length)
            elif row_header[0][1]== _MAX_INT:
                total_rows.append(row_index + group_length)
            elif row_header[2] is None and row_header[3] is None:
                if row_header[1]==' ':
                    empty_rows.append(row_index + group_length)
                else:
                    title_rows.append(row_index + group_length)
                
        if _debug:
            _logger.info('column_headers')
            _logger.info(column_headers)
            _logger.info('row_headers')
            _logger.info(row_headers)   
            _logger.info('group_rows %s' % group_rows)  
            _logger.info('total_rows %s' % total_rows)           
        
        for row_no in range(len(rows)):
            rows[row_no] = [None] * (len(column_headers) + group_length)            
        
        def extract(value):
            if isinstance(value, tuple):
                fn = lambda v : True if isinstance(v, string_types) else False
                return ', '.join(filter(fn, value))
            return value                          
        
        for record in data:
            col_no = column_headers.index(record[0]) + group_length
            row_no = row_headers.index(record[1]) + group_length
            rows[row_no][col_no]=record[2]
            if record[1][2] :
                outlines_row.add(row_no) 
                
        for row_no in sorted(outlines_row):
            parent_row_no = row_no -1
            if parent_row_no not in (outlines_row | collapse_row):
                collapse_row.add(parent_row_no)
                
            
        if self.show_transaction:                  
            for record in data: 
                if isinstance(record, tuple) and record in data_source_sql:
                    col_no = column_headers.index(record[0]) + group_length
                    row_no = row_headers.index(record[1]) + group_length         
                    budget_move_type = data_source_sql[record] ['budget_move_type']      
                    if budget_move_type:
                        model_name = 'account.budget.move.line'
                        cols_name = ['move_id','budget_id', 'date', 'general_budget_id', 'analytic_account_id','analytic_tag_ids']                
                    else:
                        model_name = 'account.move.line'      
                        cols_name = ['move_id','ref', 'name', 'date', 'account_id', 'partner_id', 'analytic_distribution','currency_id','amount_currency', 'debit', 'credit']
                    
                    details_header = ['Amount']
                    for fname in cols_name:
                        details_header.append(self.env['ir.model.fields']._get(model_name, fname).field_description)            
                                     
                    details_rows = [details_header]          
                    move_ids = []             
                    for i in range(2):
                        where = list(data_source_sql[record]['where'])
                        para = list(data_source_sql[record]['para'])
                        column_sql = data_source_sql[record]['column_sql']
                        groups_by = data_source_sql[record]['groups_by']     
                        record1 = data_source_sql[record]['record1']         
                        
                        if i:
                            sql = ['SELECT account_move_line.id,' + column_sql]
                            where.append('account_move.date >= %s')
                        else:
                            sql = ['SELECT round(coalesce(sum(%s),0), %d)' % (column_sql, decimal_places)]
                            where.append('account_move.date < %s')
                        para.append(self.transaction_date)
                        
                        for gr_idx, gr in enumerate(groups_by):
                            if gr == 'null':
                                continue                            
                            value = record1[gr_idx]
                            if value is None:
                                where.append('%s IS NULL' % gr)
                            else:
                                where.append('%s = %%s' % gr)
                                para.append(value)
                        
                        sql.append(self._get_sql_from(budget_move_type))                    
                        if where:
                            sql.append('WHERE')
                            sql.append('\nAND '.join(where))
                        
                        if i:
                            sql.append('ORDER BY account_move.date,account_move.name,account_move_line.id')
                        
                        sql = '\n'.join(sql)
                        sql = self._fix_sql(sql)   
                        if _debug:
                            _logger.info([row_no, col_no])
                            _logger.info(record1)
                            _logger.info(sql % tuple(para))         
                        cr.execute(sql, para)
                        if i:
                            for line_id, amt in cr.fetchall():                                
                                line = self.env[model_name].browse(line_id)
                                move_ids.append(line.move_id.id)
                                row = [amt]
                                for fname in cols_name:
                                    value = line[fname]
                                    if fname=='move_id':
                                        value = value.name
                                    elif fname =="analytic_distribution" and value:
                                        res = []
                                        for analytic_account_id, percentage in value.items():
                                            analytic_account_id = int(analytic_account_id)
                                            analytic_account_id = self.env['account.analytic.account'].browse(analytic_account_id)
                                            res.append(f"{analytic_account_id.name} ({percentage}%)")
                                        value = '\n'.join(res)
                                    elif isinstance(value, date):
                                        value = self.env['ir.qweb.field.date'].value_to_html(value, {})                                    
                                    elif isinstance(value, models.BaseModel):
                                        value = ','.join(value.mapped('display_name'))
                                    
                                    if value is False:
                                        value = ''
                                        
                                    row.append(value)
                                details_rows.append(row)
                        else:
                            amt,=cr.fetchone()
                            if amt:
                                row = [amt, 'Begin Balance'] + [None] * (len(details_header) -2)
                                details_rows.append(row)
                                move_ids.append(False)
                    data_source.append((row_no, col_no, details_rows, move_ids))
                    data_source_cell.append((row_no, col_no))
                                        

        def get_column_boundary(group_index, *sequences):
            ls=[]
            for sequence in filter(None,sequences):
                sequence= int(sequence)
                for col_no, col in enumerate(column_headers):
                    if col[0] == (group_index, sequence):
                        ls.append(col_no)
            if not ls:
                return None
            return min(ls)+group_length, max(ls)+group_length
        
        get_row_no = lambda row_index : row_index+group_length+1
                    
        for col_no, col in enumerate(column_headers):
            if isinstance(col[0], tuple) and len(col[0])==2:
                _, col_sequence = col[0]
                if self.columns.filtered(lambda column : column.sequence == col_sequence)[:1].hidden:
                    hidden_columns.append(col_no + group_length)                
            
            
            if isinstance(col[2], tuple) and len(col[2]) == 4:
                rows[0][col_no + group_length] = col[1]
                group_index=col[0][0]
                func, operand_type, operand1, operand2 = col[2]
                if _debug:
                    _logger.info('col ' + str(col[2]))
                operand = []
                if operand_type == '1':
                    for operand0 in operand1.split(','):
                        operand.append(get_column_boundary(group_index, operand0))
                elif operand_type == '2':
                    operand.append(get_column_boundary(group_index, operand1))   
                    operand.append(get_column_boundary(group_index, operand2))  
                elif operand_type == '3':
                    operand.append(get_column_boundary(group_index, operand1,operand2))
                if _debug:
                    _logger.info('operand ' + str(operand))
                for row_no in range(len(row_headers)):             
                    if row_headers[row_no][0][1] in row_title_seq:
                        continue                            
                    cells = tuple('%s%s:%s%s' % (xl_col_to_name(op[0]),get_row_no(row_no), xl_col_to_name(op[1]),get_row_no(row_no)) if op else '0' for op in operand)               
                    if not cells:
                        continue
                    if func=='-':
                        formula = '=SUM(%s)-SUM(%s)' % cells 
                    elif func=='/':
                        formula = '=SUM(%s)/SUM(%s)' % cells          
                    elif func=='%':
                        formula = '=SUM(%s)/SUM(%s)' % cells          
                        percentage_columns.append(col_no + group_length)
                    else:    
                        formula = '=%s(%s)' % (func, ",".join(cells))
                    rows[row_no + group_length][col_no + group_length]=formula                   
            else:
                for index, name in enumerate(col[1:]):
                    rows[index][col_no + group_length] = extract(name)
                
        def get_row_boundary(group_index, *sequences):
            ls=[]
            for sequence in filter(None,sequences):
                sequence = int(sequence)
                for row_no, row in enumerate(row_headers):
                    if row[0] == (group_index, sequence):
                        ls.append(row_no)
            if not ls:
                return None
            return get_row_no(min(ls)), get_row_no(max(ls))                                        
                
        for row_no, row in enumerate(row_headers):                 
            if isinstance(row[0], tuple) and len(row[0])==2:
                _, row_sequence = row[0]
                if self.rows.filtered(lambda row : row.sequence == row_sequence)[:1].hidden:
                    hidden_rows.append(row_no + group_length)                
            
            if isinstance(row[2], tuple) and len(row[2])==4:
                rows[row_no + group_length][0] = row[1]
                summary_rows.append(row_no + group_length)
                group_index=row[0][0]                
                func, operand_type, operand1, operand2 = row[2]
                operand = []
                if operand_type == '1':
                    for operand0 in operand1.split(','):
                        operand.append(get_row_boundary(group_index, operand0))
                elif operand_type == '2':
                    operand.append(get_row_boundary(group_index, operand1))   
                    operand.append(get_row_boundary(group_index, operand2))  
                elif operand_type == '3':
                    operand.append(get_row_boundary(group_index, operand1,operand2))
                for col_no in range(len(column_headers)):       
                    if column_headers[col_no][0][1] in column_title_seq:
                        continue           
                    col_name = xl_col_to_name(col_no+group_length)  
                    cells = tuple('%s%s:%s%s' % (col_name, op[0], col_name, op[1],) if op else '0' for op in operand)                    
                    if func=='-':
                        formula = '=SUM(%s)-SUM(%s)' % cells 
                    elif func=='/':
                        formula = '=SUM(%s)/SUM(%s)' % cells          
                    elif func=='%':
                        formula = '=SUM(%s)/SUM(%s)' % cells       
                        percentage_rows.append(row_no + group_length)                           
                    else:    
                        formula = '=%s(%s)' % (func, ",".join(cells))
                    rows[row_no + group_length][col_no + group_length]=formula   
            else:
                for index, name in enumerate(row[1:]):
                    rows[row_no + group_length][index] = extract(name)
                            
            
        if _debug:
            _logger.info('rows')
            for index,row in enumerate(rows):
                _logger.info('[%s] %s' % (index, row))    
                
        def openpyxl_func(wb, ws, set_attr):
            if not budget_move_type:
                for ws_index, _ws in enumerate(wb._sheets):
                    if ws_index == 0:
                        continue
                    for cell in _ws['H']:
                        cell.alignment = Alignment(wrap_text=True)
                          
            self._openpyxl_func(wb, ws, set_attr, html)             
                    
        data =dict(rows =rows,
                  action = 'record',
                  worksheet_name = 'report',
                  decimal_places=decimal_places, 
                  header_rows_count=group_length,
                  header_columns_count =group_length,
                  add_column_total = self.add_summary_column and self.summary_column_func,
                  add_row_total = self.add_summary_row and self.summary_row_func,
                  filename = self.name,
                  group_rows = group_rows,
                  total_rows = total_rows,
                  parameter = parameter,
                  summary_rows = summary_rows,
                  pdf = pdf,
                  empty_rows = empty_rows,
                  title_rows = title_rows,
                  outlines_row = not pdf and (not html or self.report_id) and list(outlines_row) or [],
                  outline_below = False,
                  percentage_columns = percentage_columns,
                  percentage_rows = percentage_rows,
                  html = html,
                  openpyxl_func = openpyxl_func,
                  
                  hidden_rows = hidden_rows,
                  hidden_columns = hidden_columns,
                  
                  data_source = data_source)
        
        
        if self.report_id and (pdf or html):
            rows = self.env['oi_excel_export']._eval_rows(rows)                    
            data.update({
                "wizard_id" : self.id,
                'collapse_row' : list(collapse_row),
                'col_count' : rows and rows[0] and len(rows[0]) or 0,
                'data_source_cell' : data_source_cell
                })
            self.write({'data' : json.dumps(data, default = lambda item : repr(item))})
            data = {'active_id' : self.id}            
            action = self.report_id.with_context(active_model = self._name, active_ids = self.ids).report_action(self.ids, data = data)
            if html:
                action['report_type'] = 'qweb-html'
            return action

                    
        excel_id= self.env['oi_excel_export'].export(**data) 
        
        excel_record = self.env['oi_excel_export'].browse(excel_id)
        if (pdf or html) and self._context.get('preview'):
            return excel_record.action_preview_pdf('Preview')
        
        if self._context.get('lock_report'):
            return excel_record
        
        return excel_record.action_download()
  
                        
    @api.model
    def _create_sql_functions(self):
        f = odoo.modules.get_module_resource('oi_financial_report', 'data', 'function.sql')
        with odoo.tools.misc.file_open(f) as sql_file:
            self._cr.execute(sql_file.read())
        
                                