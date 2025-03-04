from odoo import _, api, fields, models



class RESUserNFC(models.Model):
    _name = 'res.users.nfc'
    _description = 'NFC Cards Line'

    card_id = fields.Char(string="ID", )
    name = fields.Char(string="Name", )
    user_id = fields.Many2one(comodel_name='res.users', string='Users')
    is_primary = fields.Boolean('IS Primary Card?',
    default=False
    )

