'''
Created on Oct 21, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields

class AgedPartnerLineAbstract(models.AbstractModel):
    _name = 'oi_fin.aged.partner.line'
    _description = 'Aged Partner Abstract Line'
    _order = 'sequence'
    
    sequence = fields.Integer()
    name = fields.Char(required = True, translate=True)
    condition = fields.Selection([('>', 'Greater Than'), ('<', 'Less Than'), ('between', 'Between')])
    
    period_1 = fields.Integer()
    period_2 = fields.Integer()
    
    def _check_condition(self, days):
        if not self.condition:
            return True
        if self.condition == '>':
            return days > self.period_1
        if self.condition == '<':
            return days < self.period_1
        return days >= self.period_1 and days <= self.period_2
                