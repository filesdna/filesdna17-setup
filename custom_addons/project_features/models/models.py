# -*- coding: utf-8 -*-

from odoo import models, fields, api

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class NamaModel(models.Model):
    _inherit = 'project.task'


    display_type = fields.Selection(
        selection=[
            ('line_section', "Section"),
            ('line_note', "Note"),
        ],
        default=False)

    progress  = fields.Float(string='Progress',compute='_compute_progress',)

    @api.depends('child_ids','child_ids.state','child_ids.name')
    def _compute_progress(self):
        for record in self:
            percentage = 0
            nmber_of_task = len(record.child_ids)
            done_task = self.env['project.task'].search_count([('id','in',record.child_ids.ids),('state','=','1_done')])
            if nmber_of_task != 0:
                percentage = (done_task/nmber_of_task)*100
                record.progress = percentage
            else:
                record.progress = 100
            for child in record.child_ids:
                if child.state == "1_done":
                    for ch in child.child_ids:
                        ch.state = '1_done'
    
    @api.depends('child_ids','child_ids.state')
    def _compute_child_state(self):
        for record in self:
            for child in record.child_ids:
                if child.state == "1_done":
                    for ch in child.child_ids:
                        ch.state = '1_done'

    

