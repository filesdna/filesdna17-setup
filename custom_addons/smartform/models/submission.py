from odoo import models, fields, api

class Submission(models.Model):
    _name = 'submission'
    _description = 'Submission Model'

    # Fields
    form_id = fields.Char(string='Form ID', required=True)
    data = fields.Json(string='Data', required=True)
    from_user = fields.Char(string='From', default='')
    status = fields.Selection([
        ('0', 'Pending'),
        ('1', 'Approved'),
        ('2', 'Rejected')
    ], default='0', string='Status')
