from odoo import models, fields

class UserSignature(models.Model):
    _name = 'user.signature'
    _description = 'User Signature'

    user_id = fields.Many2one('res.users', string="User", required=True)
    full_name = fields.Char(string="Full Name")
    initial_name = fields.Char(string="Initial Name")
    full_signature = fields.Char(string="Full Signature", required=True)
    initial_signature = fields.Char(string="Initial Signature", required=True)
    signature_font = fields.Char(string="Signature Font")
    signature_hash = fields.Char(string="Signature Hash", required=True)
    type = fields.Selection([
        ('choose', 'Choose'),
        ('draw', 'Draw'),
        ('upload', 'Upload'),
    ], string="Type", required=True)
    default = fields.Selection([
        ('1', 'Active'),
        ('0', 'Deactive'),
    ], string="Default", default='0', required=True)
    date = fields.Char(string="Date", required=False)
    reason = fields.Text(string="Reason", required=False)
    sign_by = fields.Char(string="Signed By", required=False)
    signature = fields.Text(string="Signature", required=False)
    initial = fields.Text(string="Initial", required=False)
    no_design = fields.Selection([
        ('1', 'Yes'),
        ('0', 'No'),
    ], string="No Design", default='0')
