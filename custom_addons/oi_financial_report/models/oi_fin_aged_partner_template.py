'''
Created on Oct 21, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields

class AgedPartnerTemplate(models.Model):
    _name = 'oi_fin.aged.partner.template'    
    _description = 'Aged Partner Template'
    _inherit = 'oi_fin.aged.partner'
    _order = 'name'
    
    line_ids = fields.One2many('oi_fin.aged.partner.template.line', 'template_id', copy = True)
    name = fields.Char(required = True, translate=True)
    active = fields.Boolean(default = True)