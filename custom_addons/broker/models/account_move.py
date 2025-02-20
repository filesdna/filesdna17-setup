from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BSAccountMove(models.Model):
    _inherit = 'account.move'

    broker_id = fields.Many2one('res.partner', string='Broker', tracking=True, index=True)
    deal_type = fields.Selection(selection=[
        ('perc', 'Percentage'),
        ('amt', 'Amount'),
    ], string='Deal Type', required=True, copy=False, tracking=True, default='perc')
    rate = fields.Float(digits=0, string='Rate', help='Rate of the Deal, either percentage or amount')
    margin = fields.Float(digits=0, string='Margin', help='Margin of the Deal')
    deal_entry_id = fields.Many2one('account.move', string='Brokerage JE', copy=False, tracking=True, readonly=True)

    def action_post(self):
        res = super(BSAccountMove, self).action_post()

        #Validations
        error_msg = ''
        if not self.broker_id or self.move_type != 'out_invoice':
            return res
        journal_id = self.env['ir.config_parameter'].sudo().get_param('broker.journal_id')
        cr_account_id = self.env['ir.config_parameter'].sudo().get_param('broker.cr_account_id')
        dr_account_id = self.env['ir.config_parameter'].sudo().get_param('broker.dr_account_id')

        if self.deal_type == 'amt' and self.rate > self.amount_untaxed:
            error_msg += "- Rate should not go beyond the Untaxed Amount  \n"
        elif self.deal_type == 'perc' and self.rate > 100:
            error_msg += "- Rate should not go beyond 100%'  \n"
        if not journal_id:
            error_msg += "- Brokerage Journal not found in the parameters. \n"
        if not cr_account_id:
            error_msg += "- Brokerage Credit Account not found in the parameters.\n"
        if not dr_account_id:
            error_msg += "- Brokerage Debit Account not found in the parameters.\n"
        if error_msg:
            raise UserError(error_msg)

        #Journal Entry Generation
        deal_amount = self._get_deal_amount()
        self.margin = self.amount_untaxed - deal_amount
        self._generate_entry(deal_amount,journal_id,cr_account_id,dr_account_id)


    def _generate_entry(self, deal_amount, journal_id, cr_account_id, dr_account_id):

        # Prepare vals to create journal entry
        journal_entry_vals = {
            'ref': self.name or '',
            'move_type': 'entry',
            'date': self.date,
            'journal_id': int(journal_id),
            'currency_id': self.currency_id.id,
        }

        # Create a journal entry
        journal_entry = self.env['account.move'].create(journal_entry_vals)

        # Prepare journal items vals
        journal_items = [{
            'name': self.name or '',
            'date_maturity': self.date,
            'debit': deal_amount,
            'credit': 0.0,
            'account_id': dr_account_id,
        },
            {
            'name': self.name or '',
            'date_maturity': self.date,
            'debit': 0.0,
            'credit': deal_amount,
            'account_id': cr_account_id,
        }]

        journal_items_ids = [(0, 0, item_vals) for item_vals in journal_items]
        journal_entry.write({
            'line_ids': journal_items_ids
        })
        journal_entry.action_post()
        self.deal_entry_id = journal_entry


    def button_draft(self):
        # OVERRIDE to update the cancel date.
        res = super(BSAccountMove, self).button_draft()
        self.deal_entry_id.with_context(force_delete=True).unlink()
        self.deal_entry_id = False
        self.margin = 0.0
        return res

    def _get_deal_amount(self):
        if self.deal_type == 'perc':
            amt = self.amount_untaxed * (self.rate/100)
        else:
            amt = self.rate
        return amt

