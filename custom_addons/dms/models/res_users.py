
# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import hashlib


class ResUsers(models.Model):
    _inherit = 'res.users'

    encription_key = fields.Char(string='Encription Key' , related='company_id.encription_key', readonly=True, store=True)
    encription_type = fields.Selection(string='Encription Type', selection=[('user', 'User'), ('company', 'Company'),], default='user')
    is_auto_lock = fields.Boolean(string='Auto Lock Fiels', default=False)
    
