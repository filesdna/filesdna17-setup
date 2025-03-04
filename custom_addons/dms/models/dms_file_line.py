# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class DmsFileLine(models.Model):

    _name = 'dms.file.line'

    parent_file_id = fields.Many2one(comodel_name='dms.file', string='Parent File')
    file_id = fields.Many2one(comodel_name='dms.file', string='File')
    notes = fields.Char(string='Notes')
    
    
