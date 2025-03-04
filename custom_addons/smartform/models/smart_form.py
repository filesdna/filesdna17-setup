from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SmartForm(models.Model):
    _name = 'smart.form'
    _description = 'Smart Form'

    name = fields.Char(required=True)
    type = fields.Selection([('form', 'Form'), ('folder', 'Folder')], required=True)
    folder_id = fields.Integer(required=True)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, readonly=True)
    team_id = fields.Integer(default=0)
    hash = fields.Char()
    is_trash = fields.Boolean(default=False)
    form_data = fields.Text(default='')
    folder_ref = fields.Integer(default=0)
