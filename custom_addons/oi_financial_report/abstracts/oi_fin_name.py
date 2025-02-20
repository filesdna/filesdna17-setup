'''
Created on Oct 24, 2016

@author: Zuhair
'''

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class NameUnique(models.AbstractModel):
    
    _name = 'oi_fin.name'
    _description = 'oi_fin.name'
    
    name = fields.Char(required=True, translate = True)
    description = fields.Char()

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The name of the source must be unique !')
    ]         
        
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = default or {}
        default.setdefault('name', _("%s (copy)") % (self.name))
        return super(NameUnique, self).copy(default)
    