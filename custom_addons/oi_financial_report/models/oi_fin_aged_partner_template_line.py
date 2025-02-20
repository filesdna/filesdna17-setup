'''
Created on Oct 21, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields

class AgedPartnerTemplateLine(models.Model):
    _name = 'oi_fin.aged.partner.template.line'    
    _description = 'Aged Partner Template Line'
    _inherit = 'oi_fin.aged.partner.line'
    
    template_id = fields.Many2one('oi_fin.aged.partner.template', required = True, ondelete = 'cascade', copy = False)