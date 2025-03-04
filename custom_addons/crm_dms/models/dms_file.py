# -*- coding: utf-8 -*-

from odoo import models, fields, api


class DMSCRM(models.Model):
    _inherit = 'dms.file'

    lead_id = fields.Many2one(comodel_name='crm.lead', string='Case')

