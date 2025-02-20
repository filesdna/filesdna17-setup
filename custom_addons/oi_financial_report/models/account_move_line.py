'''
Created on Nov 27, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    
    debit_cash_basis = fields.Monetary(currency_field='company_currency_id', compute='_compute_cash_basis', store=True)
    credit_cash_basis = fields.Monetary(currency_field='company_currency_id', compute='_compute_cash_basis', store=True)
    balance_cash_basis = fields.Monetary(compute='_compute_cash_basis', store=True, currency_field='company_currency_id',
        help="Technical field holding the debit_cash_basis - credit_cash_basis in order to open meaningful graph views from reports")
    
    @api.depends('debit', 'credit', 'balance', 'move_id.matched_percentage', 'move_id.journal_id')
    def _compute_cash_basis(self):
        for move_line in self:
            move_line.debit_cash_basis = move_line.debit * move_line.move_id.matched_percentage
            move_line.credit_cash_basis = move_line.credit * move_line.move_id.matched_percentage
            move_line.balance_cash_basis = move_line.debit_cash_basis - move_line.credit_cash_basis

    