'''
Created on Oct 16, 2016

@author: Zuhair
'''

from odoo import models, fields, api
from odoo.exceptions import UserError
from ..Common import SQL_FROM
import logging


_logger = logging.getLogger(__name__)

SQL_ORDER = """
ORDER BY account_move.date, account_move.id, account_move_line.id
"""

class Data(models.TransientModel):
    
    _name = 'oi_fin.data'
    _description = 'oi_fin.data'
    _inherit = ['oi_fin.group']
    
    begin_balance = fields.Boolean('Show Begin Balance')
    name = fields.Char()
    
    template = fields.Many2one('oi_fin.datatmpl', store = False)
    
    col_company =fields.Boolean('Show Company', sql_select = 'res_company.name', sql_order = 0)
    
    col_move_name =fields.Boolean('Entry Number', sql_select = 'account_move.name', sql_order = 10)
    col_move_ref =fields.Boolean('Entry Reference', sql_select = 'account_move.ref', sql_order =20)
    col_move_date =fields.Boolean('Entry Date', default = True, sql_select = 'account_move.date', sql_order = 30)
    col_move_month =fields.Boolean('Entry Month', default = False, sql_select = "to_char(account_move.date,'mm/yyyy')", sql_order = 31)
    col_move_state =fields.Boolean('Entry Status', sql_select = "case when account_move.state ='draft' then 'Unposted' else 'Posted' end", sql_order = 30)
        
    col_move_narration =fields.Boolean('Internal Note', sql_select = 'account_move.narration', sql_order = 31)
    col_move_line_name =fields.Boolean('Entry Label', sql_select = 'account_move_line.name', sql_order = 32)
                
    col_journal =fields.Boolean('Journal', sql_select = 'account_journal.name', sql_order = 40) 
    col_account_name =fields.Boolean('Account Name', default = True, sql_select = 'account_account.name', sql_order = 60)     
    col_account_code =fields.Boolean('Account Code', default = True, sql_select = 'account_account.code', sql_order = 50)
    col_account_type =fields.Boolean('Account Type', sql_select = 'account_account_type.name', sql_order = 70)
    col_account_tag =fields.Boolean('Account Tag', sql_order = 80, sql_select = """(select string_agg(t.name,', ') 
            from account_account_tag t 
            where exists (select 1 
                from account_account_account_tag at 
                where at.account_account_id=account_account.id 
                and at.account_account_tag_id = t.id  ))
                """)
    
    col_debit = fields.Boolean('Debit', default = True, sql_select = 'account_move_line.debit', sql_order = 90)  
    col_credit = fields.Boolean('Credit', default = True, sql_select = 'account_move_line.credit', sql_order = 100)  
    #col_balance = fields.Boolean('Balance', sql_select = '(account_move_line.debit - account_move_line.credit)', sql_order = 110)  
    col_balance = fields.Selection([('dr','Debit - Credit'),('cr','Credit - Debit')], string='Balance',
                                   sql_select = {'dr': 'account_move_line.balance','cr': '-account_move_line.balance'},
                                   sql_order = 110)
    
    balance_acc = fields.Boolean('Accumulative')
   
    col_analytic_code = fields.Boolean('Analytic Account Reference', sql_select = 'account_analytic_account.code', sql_order = 120) 
    col_analytic_name = fields.Boolean('Analytic Account', sql_select = 'account_analytic_account.name', sql_order = 130)
    col_analytic_group_name = fields.Boolean('Analytic Account Group', sql_select = 'account_analytic_group.complete_name', sql_order = 135)  
    col_analytic_tag =fields.Boolean('Analytic Account Tag', sql_order = 140, sql_select = """(select string_agg(t.name,', ') 
            from account_analytic_tag t 
            where exists (select 1 
                from account_analytic_tag_account_move_line_rel at 
                where at.account_move_line_id=account_move_line.id 
                and at.account_analytic_tag_id = t.id  ))
                """)   
    
    col_partner_name = fields.Boolean('Partner', sql_select = 'res_partner.name', sql_order = 150)  
    col_partner_ref = fields.Boolean('Partner Reference', sql_select = 'res_partner.ref', sql_order = 160) 
    col_partner_country = fields.Boolean('Partner Country', sql_select = 'res_country.name', sql_order = 170) 
    col_partner_tag =fields.Boolean('Show Partner Tags', sql_order = 180, sql_select = """(select string_agg(t.name,', ') 
            from res_partner_category t 
            where exists (select 1 
                from res_partner_res_partner_category_rel pc 
                where pc.partner_id = res_partner.id
                and pc.category_id = t.id  ))
                """)   
    
    col_product_code = fields.Boolean('Product Reference', sql_select = 'product_product.default_code', sql_order = 190)
    col_product_name = fields.Boolean('Product', sql_select = 'product_template.name', sql_order = 200)                
    col_product_category = fields.Boolean('Product Category', sql_select = 'product_category.name', sql_order = 210)
    col_product_quantity =fields.Boolean('Quantity', sql_select = 'account_move_line.quantity', sql_order = 220) 
    col_product_uom =fields.Boolean('Unit of Measure', sql_select = 'product_uom.name', sql_order = 230) 
    
    col_bank_statement_name =fields.Boolean('Bank Statement', sql_select = 'account_bank_statement.name', sql_order = 240)  
    col_bank_statement_date =fields.Boolean('Bank Statement Date', sql_select = 'account_bank_statement.date', sql_order = 250)
    col_bank_statement_line_date =fields.Boolean('Bank Statement Line Date', sql_select = 'account_bank_statement_line.date', sql_order = 260)
    col_bank_statement_line_name =fields.Boolean('Bank Statement Line Memo', sql_select = 'account_bank_statement_line.name', sql_order = 270)
    col_bank_statement_line_ref =fields.Boolean('Bank Statement Line Reference', sql_select = 'account_bank_statement_line.ref', sql_order = 280)
    col_bank_statement_line_note =fields.Boolean('Bank Statement Line Notes', sql_select = 'account_bank_statement_line.note', sql_order = 280)            
        
    cash_basis = fields.Boolean('Cash Basis')
    
    def _valid_field_parameter(self, field, name):
        return name in ['sql_select', 'sql_order'] or super()._valid_field_parameter(field, name)
    
    
    @api.onchange('template')
    def on_template_change(self):
        if self.template:
            self.copy_template(self.template, self)
            
    def copy_template(self, obj_from, obj_to):        
        for field_name, field in obj_from._fields.items():
            if field_name in ('date_from', 'date_to'):
                continue
            if field_name not in obj_to._fields:
                continue
            if field.automatic or field.compute:
                continue
            value = getattr(obj_from, field_name)                      
            if field.type =='many2many':
                value = [(6,0, value._ids)]                
            setattr(obj_to, field_name, value)             
           
                    
            
    def create_template(self):
        self.ensure_one()
        if not self.name:
            raise UserError('Enter Name')
        tmpl = self.env['oi_fin.datatmpl']
        if tmpl.search_count([('name','=', self.name)]):
            raise UserError('Name already exists')
        tmpl = tmpl.create(dict(name=self.name))
        self.copy_template(self, tmpl)
        self.template = tmpl         
        self.env.cr.commit()      
        raise UserError('Template Created (%s)' % self.name)
                                             
    def _get_sql_select(self, begin_balance = False):
        select = []        
        
        def field_string(field):
            res = self.fields_get(allfields = [field], attributes = ['string'])
            return res[field].get('string', field)
        
        def add(field, sql,sql_order):
            value = getattr(self, field)
            if value:
                if isinstance(sql, dict):
                    sql = sql[value]
                if begin_balance:
                    if field not in ('col_debit', 'col_credit','col_balance','col_product_quantity'):
                        sql = "null"
                    else:
                        sql = 'coalesce(sum(%s),0)' % sql
                if self.cash_basis:
                    for v in ['debit', 'credit', 'balance']:
                        sql = sql.replace(v, '%s_cash_basis' % v)
                select.append((sql_order,sql, field_string(field),field.endswith('_date') ))
                
        for name, field in self._fields.items():
            if name.startswith('col_'):
                add (name, getattr(field, 'sql_select'), getattr(field, 'sql_order'))
                
        select = sorted(select)
        date_cols = [index for index,rec in enumerate(select) if rec[3]]
        balance_col = -1
        col_balance_string=field_string('col_balance')
        for index,rec in enumerate(select):
            if rec[2]==col_balance_string:
                balance_col=index
                break
        select = ['%s AS "%s"' % (rec[1],rec[2]) for rec in select]
                
        return select, date_cols, balance_col if self.balance_acc else False
    
    def _get_sql_para(self, begin_balance = False, group = None, group_filter=None):
        where , para = self._get_sql_where(begin_balance = begin_balance)
        self._add_company_filter(where,para)
        select,date_cols, balance_col = self._get_sql_select(begin_balance = begin_balance)
        if group:
            if group[0]:
                group_filter = group_filter + ' = %s' 
                para.append(group[0])
            else:
                group_filter = group_filter  + ' IS NULL'
            where.append(group_filter)
            
        sql = [] 
        sql.append('SELECT ')
        sql.append(",\n".join(select))
        sql.append(SQL_FROM)        
        if where:
            sql.append('WHERE ')
            sql.append("\nAND ".join(where))
        if not begin_balance:
            sql.append(SQL_ORDER)
        sql = "\n".join(sql)        
        return sql, para, date_cols, balance_col
    
    
    def run_report_pdf(self):
        return self.with_context(pdf = True).run_report()
    
    
    def run_report(self):                
        self.env['account.move'].check_access_rights('read')
        
        pdf = self._context.get('pdf', False)
        
        self.ensure_one()      
        rows= []
        cr = self.env.cr
        summary_rows = []
        group_rows= []
        column_count = 0
        total_rows=[]
        date_cols=[]
        
        parameter = False #self.get_parameter_info()
        
        def add_column_names():
            if not rows and not column_count:                 
                column_names = [row[0] for row in cr.description]
                rows.append(column_names)       
                return len(column_names)
            return column_count
        
        def add_empty_row():
            rows.append([None] * column_count )
            
        groups, group_filter = self.get_groups(self.begin_balance)
        
        for group in groups:
            
            group_header = False
            
            def add_group_header():                
                if group and not group_header:
                    group_rows.append(len(rows))
                    rows.append(group[1:])                                               
                        
            if self.begin_balance:
                sql,para,date_cols, balance_col = self._get_sql_para(begin_balance = True, group= group, group_filter=group_filter)  # @UnusedVariable
                cr.execute(sql, para)
                column_count=add_column_names()
                add_group_header()
                group_header = True
                summary_rows.append(len(rows))          
                balance_row = list(cr.fetchall()[0])
                rows.append(balance_row)
                                    
            sql,para,date_cols, balance_col = self._get_sql_para(begin_balance = False, group= group, group_filter=group_filter)
            cr.execute(sql, para)
            column_count=add_column_names()
            add_group_header()            
            group_row_index = len(rows)-1       
            rows.extend(cr.fetchall())     
            if balance_col and balance_col > -1:
                balance = 0
                for index,row in enumerate(rows):
                    if index >= group_row_index and balance_col < len(row):
                        row = list(row)
                        balance += row[balance_col] if isinstance(row[balance_col], (float,int)) else 0
                        row[balance_col] = balance    
                        rows[index]=row                    
            elif group:
                total_rows.append(len(rows))
                add_empty_row()
        add_row_total = not (self.col_balance and self.balance_acc) and 'SUM'
        data = dict(rows= rows,
                    date_cols = date_cols, 
                    summary_rows = summary_rows, 
                    group_rows= group_rows, 
                    total_rows=total_rows, 
                    filename = self.name,
                    parameter = parameter,
                    pdf = pdf,
                    add_row_total = add_row_total)
        
        if self._context.get('lock_report'):
            data['action'] = 'record'
            excel_id= self.env['oi_excel_export'].export(**data)
            return self.env['oi_excel_export'].browse(excel_id)
        
        return self.env['oi_excel_export'].export(**data)
        