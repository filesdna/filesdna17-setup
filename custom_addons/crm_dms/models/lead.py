# -*- coding: utf-8 -*-

from odoo import models, fields, api , _


class LAWYER(models.Model):
    _inherit = 'crm.lead'


    dms_line_ids = fields.Many2many(comodel_name='dms.file',inverse_name='lead_id', string='DMS')


    

