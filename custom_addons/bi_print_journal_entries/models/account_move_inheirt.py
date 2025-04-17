from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    voucher_type = fields.Selection([
        ('receive', 'Receive'),
        ('send', 'Send'),
    ])
    name_of_journal = fields.Char(compute='_compute_name_of_journal')

    @api.depends('voucher_type', 'journal_id')
    def _compute_name_of_journal(self):
        for rec in self:
            if rec.voucher_type:
                print("inside _compute_name_of_journal")
                # print("journal_id=", rec.journal_id.name)
                # print("voucher_type=", rec.voucher_type)
                rec.name_of_journal = rec.journal_id.name + '/' + rec.voucher_type
            else:
                rec.name_of_journal = rec.journal_id.name