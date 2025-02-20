'''
Created on Oct 21, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields

class AgedPartnerAbstract(models.AbstractModel):
    _name = 'oi_fin.aged.partner'
    _description = 'Aged Partner Abstract'
    
    partner_tag_ids = fields.Many2many('res.partner.category', string='Partner Tags')
    partner_ids = fields.Many2many('res.partner', string='Partners')
    type = fields.Selection([('asset_receivable', 'Receivable'), ('liability_payable', 'Payable')], string='Account Type')
    account_ids = fields.Many2many('account.account', string='Accounts')
    show_details = fields.Boolean()
    
    show_payment_terms = fields.Boolean()
    show_salesperson_name = fields.Boolean()
    show_salesperson_reference = fields.Boolean()

    show_analytic_account_name = fields.Boolean()
    show_analytic_account_reference = fields.Boolean()
    show_analytic_tags= fields.Boolean()
    
    currency_id = fields.Many2one('res.currency')