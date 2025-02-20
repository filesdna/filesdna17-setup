from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_starting_sequence(self):
        # EXTENDS account sequence.mixin
        self.ensure_one()

        starting_sequence = "%s/%04d/00000" % (self.journal_id.code, self.date.year)
        if self.journal_id.refund_sequence and self.move_type in ('out_refund', 'in_refund'):
            starting_sequence = "R" + starting_sequence
            print('starting_sequence_refund=', starting_sequence)
        if self.journal_id.payment_sequence and self.payment_id:
            starting_sequence = "P" + starting_sequence
            print('starting_sequence_payment=', starting_sequence)

        return starting_sequence
