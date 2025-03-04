'''
Created on Oct 21, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields

class AgedPartnerWizardLine(models.TransientModel):
    _name = 'oi_fin.aged.partner.wizard.line'
    _description = 'Aged Partner Wizard Line'
    _inherit = 'oi_fin.aged.partner.line'
    
    wizard_id = fields.Many2one('oi_fin.aged.partner.wizard', required = True, ondelete = 'cascade')