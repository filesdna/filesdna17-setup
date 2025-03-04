from odoo import api, models, fields


class MailMAilINherit(models.Model):
    _inherit = 'mail.mail'

    @api.model_create_multi
    def create(self, values):
        res = super(MailMAilINherit, self).create(values)
        return res
