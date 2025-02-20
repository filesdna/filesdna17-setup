'''
Created on Nov 27, 2019

@author: Zuhair Hammadi
'''
from odoo import models, api, fields
from odoo.tools.float_utils import float_is_zero

class AccountMove(models.Model):
    _inherit = "account.move"
    
    matched_percentage = fields.Float('Percentage Matched', compute='_compute_matched_percentage', digits=0, store=True, readonly=True, help="Technical field used in cash basis method")
    
    @api.depends('amount_total','amount_residual','move_type')
    def _compute_matched_percentage(self):
        """Compute the percentage to apply for cash basis method. This value is relevant only for moves that
        involve journal items on receivable or payable accounts.
        """
        for move in self:
            if not move.is_invoice(True) or move.currency_id.is_zero(move.amount_total):
                move.matched_percentage = 1
                continue
            
            paid_amount = move.amount_total - move.amount_residual
            move.matched_percentage = paid_amount / move.amount_total
