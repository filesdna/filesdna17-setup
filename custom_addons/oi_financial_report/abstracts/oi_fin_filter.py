'''
Created on Oct 20, 2016

@author: Zuhair
'''
from odoo import models, fields, api, _
from ..Common import extract_ids,get_sql_value,get_date_str
import logging
from odoo.tools import config
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)
_debug = config.get('debug.oi_financial_report')

class Filter(models.AbstractModel):
    
    _name = 'oi_fin.filter'
    _description = 'oi_fin.filter'
    _inherit = []
    
    def _get_country_domain(self):
        self.env.cr.execute('select distinct country_id from res_partner where country_id is not null')
        ids = extract_ids(self.env.cr.fetchall())
        return [('id','in', ids)]
    
    def _get_company_domain(self):
        return [('id','in', self.env.user.company_ids.ids)]    
    
    company_ids = fields.Many2many('res.company', string='Company', default = False, domain = _get_company_domain)
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')
   
    target_move = fields.Selection([('posted', 'Posted Entries'),
                                    ('all', 'All Entries'),
                                    ('draft', 'Unposted')
                                    ], string='Target Moves', required=True, default='all')    
    
    
    account_tag_ids = fields.Many2many('account.account.tag', string='Account Tags')
    account_type_ids = fields.Many2many('oi_fin.account.type', string='Account Types')
    account_ids = fields.Many2many('account.account', string='Accounts')
    
    analytic_ids = fields.Many2many('account.analytic.account', string='Analytic Accounts')
    analytic_plan_ids = fields.Many2many('account.analytic.plan', string='Analytic Plans')          
    
    partner_category_ids = fields.Many2many('res.partner.category', string='Partner Tags')
    country_ids = fields.Many2many('res.country', string='Partner country', domain = _get_country_domain) 
    partner_ids = fields.Many2many('res.partner', string='Partners')
    
    product_category_ids = fields.Many2many('product.category', string='Product Categories') 
    product_ids = fields.Many2many('product.product', string='Products') 
    
    journal_ids = fields.Many2many('account.journal', string='Journals')
    
    multi_company = fields.Boolean(compute='_multi_company')
        
    account_group_ids = fields.Many2many('account.group', string='Account Group')
    
    account_domain = fields.Char('Account Domain')
    
    debit = fields.Boolean('Debit Only')
    credit = fields.Boolean('Credit Only')
    
    special_filter = fields.Selection([('liquidity','liquidity Entry'), 
                                       ('liquidity-related','liquidity Entry or liquidity Related'), 
                                       ], string='Special Filter')    
    
            
    @api.depends('company_ids')
    def _multi_company(self):
        count = get_sql_value(self,'select count(*) from res_company')
        for record in self:
            record.multi_company = bool(count > 1)
            
    def _add_company_filter(self, where, para):
        if self.multi_company:
            where.append('res_company.id in %s')
            para.append(self.env.user.company_ids._ids)
    
    @api.onchange('account_tag_ids','account_type_ids', 'company_ids', 'account_group_ids')
    def set_account_ids_domain(self):
        domain = []
        if self.company_ids:
            domain.append(('company_id','in',self.company_ids._origin._ids))
        if self.account_type_ids:           
            domain.append(('account_type','in',self.account_type_ids.mapped('value')))          
        if self.account_tag_ids:
            sql='select account_account_id from account_account_account_tag where account_account_tag_id in %s' 
            self.env.cr.execute(sql, (self.account_tag_ids._origin._ids,))
            ids = extract_ids(self.env.cr.fetchall())
            domain.append(('id','in', ids))
        if self.account_group_ids:
            domain.append(('group_id','in', self.account_group_ids.ids))        
        if self.account_ids:
            account_ids = self.account_ids._origin._ids
            account_ids = self.env['account.account'].search(domain + [('id','in',account_ids)])         
            account_ids = account_ids._origin._ids 
            self.account_ids = [(6, 0, account_ids)]
        return {
            'domain': {'account_ids' : domain }
            }       
        
    @api.onchange('company_ids', 'analytic_plan_ids')
    def set_analytic_ids_domain(self):
        domain = []
        if self.company_ids:
            domain.append(('company_id','in',self.company_ids._origin._ids))
        if self.analytic_plan_ids:
            domain.append(('plan_id','child_of', self.analytic_plan_ids.ids))
            
        if self.analytic_ids:
            analytic_ids = self.analytic_ids._origin._ids
            analytic_ids = self.env['account.analytic.account'].search(domain + [('id','in',analytic_ids)])
            analytic_ids = analytic_ids._origin._ids
            self.analytic_ids = [(6, 0, analytic_ids)]
        return {
            'domain': {'analytic_ids' : domain }
            }          

    @api.onchange('partner_category_ids','company_ids','country_ids')
    def set_partner_ids_domain(self):
        domain = []
        if self.company_ids:
            domain.append(('company_id','in',self.company_ids._origin._ids))
        if self.country_ids:
            domain.append(('country_id','in',self.country_ids._origin._ids))
        if self.partner_category_ids:
            sql='select partner_id from res_partner_res_partner_category_rel where category_id in %s' 
            tag_ids = self.partner_category_ids._origin._ids
            self.env.cr.execute(sql, (tag_ids,))
            ids = extract_ids(self.env.cr.fetchall())
            domain.append(('id','in', ids))            
        if self.partner_ids:
            current_ids = self.partner_ids._origin._ids
            partners =self.env['res.partner'].search(domain + [('id','in',current_ids)])  
            partners_ids = partners._origin._ids           
            self.partner_ids = [(6, 0, partners_ids)]        
        return {
            'domain': {'partner_ids' : domain }
            }
        
    @api.onchange('product_category_ids','company_ids')
    def set_product_ids_domain(self):
        domain = []
        if self.company_ids:
            domain.append(('company_id','in',self.company_ids._origin._ids))
        if self.product_category_ids:
            sql='''select pp.id
                from product_product pp
                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                where pt.categ_id in %s''' 
            categ_ids = self.product_category_ids._origin._ids
            self.env.cr.execute(sql, (categ_ids,))
            ids = extract_ids(self.env.cr.fetchall())
            domain.append(('id','in', ids))            
        if self.product_ids:
            current_ids = self.product_ids._origin._ids
            products =self.env['product.product'].search(domain + [('id','in',current_ids)])  
            product_ids = products._origin._ids           
            self.product_ids = [(6, 0, product_ids)]        
        return {
            'domain': {'product_ids' : domain }
            }  
        
    def _get_sql_where(self, begin_balance = False, date_from = None, date_to= None, res = {}, where=[],para=[], balance_type= False, row = None, column = None, case = None, budget_move_type = None ):
        """
        @return: where, para
        """
        where = list(res.get('where',where))
        para =  list(res.get('para',para))         
        
        if self.company_ids:
            where.append('account_move.company_id in %s')
            para.append(self.company_ids._ids)            

        date_from = date_from or self.date_from
        date_to = date_to or self.date_to
        
        date_from = get_date_str(date_from)        
        date_to = get_date_str(date_to)      
                    
        if balance_type=='end':
            if date_to:
                where.append('account_move.date <= %s')
                para.append(date_to)
        elif begin_balance or balance_type=='begin':
            date_from = date_from or self._context.get('date_from')
            if date_from:
                where.append('account_move.date < %s')
                para.append(date_from)               
            else:
                where.append('account_move.date IS NULL')
        else:
            if date_from:
                where.append('account_move.date >= %s')
                para.append(date_from)         
            if date_to:
                where.append('account_move.date <= %s')
                para.append(date_to)             
                
        if column and row :
            date_from = self._context.get('date_from')           
            year_start = self._context.get('year_start') or date_from

            if column.special_filter=='credit' or row.special_filter=='credit':
                if not budget_move_type:
                    where.append('credit > 0')
                else:
                    where.append('amount < 0')  
            if column.special_filter=='debit' or row.special_filter=='debit':
                if not budget_move_type:
                    where.append('debit > 0')
                else:
                    where.append('amount > 0')  
                
            if (column.special_filter =='initial_balance' and row.special_filter != 'unallocated_earnings') or (row.special_filter =='initial_balance' and column.special_filter != 'unallocated_earnings'):
                if year_start and case==[]:
                    where.append('account_account.account_type != %s')
                    para.append('equity_unaffected')       
                    where.append('(account_move.date >= %s or account_type.include_initial_balance)')    
                    para.append(year_start)                                               
            
            elif (column.special_filter =='initial_balance' and row.special_filter == 'unallocated_earnings') or (row.special_filter =='initial_balance' and column.special_filter == 'unallocated_earnings'):
                if year_start:       
                    where.append('(not account_type.include_initial_balance or account_account.account_type=%s)')
                    para.append('equity_unaffected')  
                                                                                                                 
                    where.append('(account_move.date <%s or account_account.account_type=%s)')  
                    para.append(year_start)             
                    para.append('equity_unaffected')        
                else:
                    where.append('1=2')
            if not balance_type and (row.special_filter == 'unallocated_earnings' or row.special_filter =='unallocated_earnings'):
                where.append('account_account.account_type=%s')    
                para.append('equity_unaffected')
        
        if _debug:
            _logger.info(['balance_type', balance_type])
            _logger.info(['begin_balance', begin_balance])
            _logger.info(['date_from', date_from])
            _logger.info(['date_to', date_to])
            
            
        if self.target_move and self.target_move != 'all':
            if not budget_move_type:
                where.append('account_move.state = %s')
                para.append(self.target_move)     
            else:
                if self.target_move =='posted':
                    where.append("account_move.state = 'approved'")       
                else:
                    where.append("account_move.state not in ('approved', 'rejected')")                                         
            
        if self.account_tag_ids:
            where.append('exists (select 1 from account_account_account_tag t where t.account_account_tag_id in %s and account_account.id = t.account_account_id)')
            para.append(self.account_tag_ids._ids)
        
        if self.account_type_ids:    
            where.append('account_account.account_type in %s')
            para.append(tuple(self.account_type_ids.mapped('value')))
        
        if self.account_ids:
            where.append('account_account.id in %s')
            para.append(self.account_ids._ids)            
        
        if self.analytic_ids:          
            where.append('exists (select 1 from account_analytic_account t where t.id in %s and account_move_line.analytic_distribution->t.id::text is not null)')
            para.append(self.analytic_ids._ids)       
            
        if self.analytic_plan_ids:
            where.append('exists (select 1 from account_analytic_account t where t.plan_id in %s and account_move_line.analytic_distribution->t.id::text is not null)')
            para.append(self.analytic_plan_ids._ids)       
                    
        if self.partner_category_ids and not budget_move_type:   
            where.append('exists (select 1 from res_partner_res_partner_category_rel t where t.category_id in %s and t.partner_id = res_partner.id )')
            para.append(self.partner_category_ids._ids)              
        if self.country_ids and not budget_move_type:
            where.append('res_partner.country_id in %s')
            para.append(self.country_ids._ids)                      
        if self.partner_ids and not budget_move_type:    
            where.append('res_partner.id in %s')
            para.append(self.partner_ids._ids)                  
            
        if self.product_category_ids and not budget_move_type:
            where.append('exists (select 1 from product_template pt where pt.categ_id in %s and pt.id = product_product.product_tmpl_id)' )
            para.append(self.product_category_ids._ids)               
        if self.product_ids and not budget_move_type:  
            where.append('product_product.id in %s')
            para.append(self.product_ids._ids)                 
                        
        if self.journal_ids and not budget_move_type:
            where.append('account_move.journal_id in %s')
            para.append(self.journal_ids._ids)
            
        if self.account_group_ids:
            where.append('account_group.id in %s')
            para.append(self.account_group_ids._ids)           
            
        if self.account_domain:
            account_domain = safe_eval(self.account_domain)
            account_ids=self.env['account.account'].search(account_domain)
            if account_ids:
                where.append('account_account.id in %s')
                para.append(account_ids._ids)              
            else:
                _logger.warning('no account found by domain %s' % self.account_domain)
                where.append('account_account.id = 0')   
                
        if self.debit:
            if not budget_move_type:
                where.append('debit > 0')  
            else:
                where.append('amount < 0')  
            
        if self.credit:
            if not budget_move_type:
                where.append('credit > 0') 
            else:
                where.append('amount > 0')  
            
        if self.special_filter == 'liquidity' and not budget_move_type:
            where.append("""
exists (select 1 from account_move_line ml
        inner join account_account a on a.id = ml.account_id        
        where ml.move_id = account_move.id
        and a.account_type = 'asset_cash'       
       )
            """)       
            
        if self.special_filter == 'liquidity-related' and not budget_move_type:
            where.append("""(
exists (select 1 from account_move_line ml
        inner join account_account a on a.id = ml.account_id        
        where ml.move_id = account_move.id
        and a.account_type = 'asset_cash'       
       )
or
exists (select 1 from account_move_line ml        
        inner join account_partial_reconcile pr on ml.id in (pr.credit_move_id, pr.debit_move_id)
        inner join account_move_line ml2 on ml2.id in (pr.credit_move_id, pr.debit_move_id)
        inner join account_move_line ml3 on ml3.move_id = ml2.move_id
        inner join account_account a on a.id = ml3.account_id               
        where ml.move_id = account_move.id
        and a.account_type = 'asset_cash'    
       )   
)""")      
            
        if budget_move_type and self.budget_ids:
            where.append("account_move.budget_id in %s")
            para.append(self.budget_ids._ids)
            
        if budget_move_type:
            where.append("account_move_line.type = %s")
            para.append(budget_move_type)
            
        for dimension in self.env['oi_fin.dimension'].search([('filter_code','!=', False)]):
            localdict = {
                'self' : self,
                'where' : where,
                'para' : para,
                'begin_balance' : begin_balance,
                'date_from' : date_from,
                'date_to' : date_to,
                'res' : res,
                'row' : row,
                'column' : column,
                'case' : case,
                'budget_move_type' : budget_move_type,
                }
            safe_eval(dimension.filter_code, localdict, mode='exec', nocopy=True)
                                                                          
        return where, para                                  
        
    @api.constrains('account_domain')
    def _check_account_domain(self):
        for record in self:
            if record.account_domain:
                try:
                    account_domain = safe_eval(self.account_domain)
                    self.env['account.account'].sudo().search(account_domain)
                except:
                    raise ValidationError(_('Invalid Account Domain'))                    
        