from odoo import models, fields, api, _

class SignRequest(models.Model):

    _name = 'dms.sign.request'
    _description = ''



    name = fields.Char()

