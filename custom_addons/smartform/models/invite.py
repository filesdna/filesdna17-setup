from odoo import models, fields

class Invite(models.Model):
    _name = 'invite'
    _description = 'Invite Model'

    # Fields
    form = fields.Char(string='Form', required=True)
    from_user = fields.Char(string='From', required=True)
    to_user = fields.Char(string='To', required=True)
    message = fields.Json(string='Message', required=True)
    done = fields.Selection([
        ('0', 'Pending'),
        ('1', 'Completed')
    ], default='0', string='Status')
