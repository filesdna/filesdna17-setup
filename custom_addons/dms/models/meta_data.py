# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


CATEGORY_SELECTION = [
    ('required', 'Required'),
    ('optional', 'Optional'),
    ('no', 'None')]


class MetaDataConfiguration(models.Model):

    _name = 'metadata.configuration'

    name = fields.Char(string='Name')
    has_summary = fields.Selection(CATEGORY_SELECTION, string="Has Summary", default="no")
    has_notes = fields.Selection(CATEGORY_SELECTION, string="Has Notes", default="no")
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )