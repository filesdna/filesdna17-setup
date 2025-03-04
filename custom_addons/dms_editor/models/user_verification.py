from odoo import models, fields 

class UserVerification(models.Model):
    _name = 'user.verification'
    _description = 'User Verification'

    user_id = fields.Many2one('res.users', string="User", required=True)
    is_verify_liveness = fields.Integer(string="Liveness", default=0)
    is_verify_voice = fields.Integer(string="Voice", default=0)
