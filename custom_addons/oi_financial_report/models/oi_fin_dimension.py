'''
Created on Nov 28, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields, api
from ..Common import SQL_FROM

class Dimension(models.Model):    
    _name = 'oi_fin.dimension'
    _description = 'oi_fin.dimension'
    _order = 'sequence,id'
    
    name = fields.Char(required = True)
    active = fields.Boolean(default = True)
    sequence = fields.Integer()
    sql_from = fields.Text()
    group_columns = fields.Char()
    filter_code = fields.Text()
    
    base_sql_from = fields.Text(compute = '_calc_base_sql_from')
    
    
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The name must be unique !')
    ]         
    
    @api.depends('name')
    def _calc_base_sql_from(self):
        for record in self:
            record.base_sql_from = SQL_FROM