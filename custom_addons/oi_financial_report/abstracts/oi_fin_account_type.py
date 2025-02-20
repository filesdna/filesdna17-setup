'''
Created on Oct 23, 2022

@author: Zuhair Hammadi
'''
from odoo import models, fields, tools

class AccountType(models.Model):
    _name = 'oi_fin.account.type'
    _description = 'Account Type'
    _auto = False
    
    name = fields.Char(translate = True)
    value = fields.Char()
    include_initial_balance = fields.Boolean()
        
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute('''
            CREATE OR REPLACE VIEW %s AS (
            select id, value, name,
            case
                when value like 'income%%' then false
                when value like 'expense%%' then false
                else true    
            end include_initial_balance
            from ir_model_fields_selection
            where field_id = (
                select id from ir_model_fields where model='account.account' and name='account_type'
            )
            order by 1
            )''' % (self._table,)
        )