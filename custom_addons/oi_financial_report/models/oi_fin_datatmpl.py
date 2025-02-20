'''
Created on Oct 31, 2016

@author: Zuhair
'''

from odoo import models
import logging


_logger = logging.getLogger(__name__)


class DataTemplate(models.Model):
    
    _name = 'oi_fin.datatmpl'
    _description = 'oi_fin.datatmpl'
    _inherit = ['oi_fin.data', 'oi_fin.name','oi_fin.menu']
    _template_col = 'template'
    _transient_model = 'oi_fin.data'
    _transient = False
    _abstract = False
    _transient_vacuum = None
    