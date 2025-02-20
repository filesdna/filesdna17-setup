'''
Created on Oct 19, 2016

@author: Zuhair
'''
from odoo import models, fields

class AccountAccount(models.Model):
    _inherit = "account.account"
    
    name2 = fields.Char('Additional Name')