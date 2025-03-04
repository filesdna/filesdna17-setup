from odoo import models, fields


class Task(models.Model):
    _inherit = 'project.task'

    
    images = fields.Text(
        string='Images',
    )
    