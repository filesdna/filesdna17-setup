# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CronErrorLog(models.Model):
    _description = "Error log"
    _name = 'cron.error.log'
    _inherit = ['mail.thread']
    _order = "exec_date desc"

    user_id = fields.Many2one('res.users', string="User",
                              default=lambda self: self.env.user, index=True)
    name = fields.Char(string="Cron Name", required=True, tracking=True)
    method = fields.Char(string="Method", tracking=True)
    object_action = fields.Char(string="Object", tracking=True)
    exec_date = fields.Datetime(string="Execution Date Time")
    error_details = fields.Char(string="Error details", tracking=True)
    cron_id = fields.Char(string='Cron ID')
