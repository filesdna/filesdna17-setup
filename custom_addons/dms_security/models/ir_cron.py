# -*- coding: utf-8 -*-
from odoo import models, fields

class IrCron(models.Model):
    _inherit = 'ir.cron'

    trigger_user_id = fields.Many2one('res.users', string='Trigger User')