from odoo import models, fields

class SignDelegate(models.Model):
    _name = 'sign.delegate'
    _description = 'Sign Delegate'

    user_id = fields.Many2one('res.users', string="User", required=True)
    email = fields.Char(string="Email", required=True)
    delegate_email = fields.Char(string="Delegate Email", required=True)
    delegate_first_name = fields.Char(string="Delegate First Name", required=True)
    delegate_last_name = fields.Char(string="Delegate Last Name", default="")
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    is_active = fields.Selection([
        ('1', 'Active'),
        ('0', 'Inactive'),
    ], string="Is Active", default='1')
