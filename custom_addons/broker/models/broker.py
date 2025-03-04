from odoo import models, fields, api
from datetime import date


class Broker(models.Model):
    _name = 'broker'

    partner_id = fields.Many2one('res.partner', required=1, string='Broker')
    # account_id = fields.Many2one('account.move')
    line_ids = fields.One2many('broker.line', 'broker_id')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
    ], default='draft')
    total = fields.Integer(compute='_compute_total', store=True)
    journal_entry_id = fields.Many2one('account.move', string='Journal Entry')

    @api.depends('line_ids.amount')
    def _compute_total(self):
        for rec in self:
            total_amt = 0
            total_per = 0
            for line in rec.line_ids:
                if line.deal_type == "amt":
                    total_amt += line.amount
                else:
                    total_per += int(line.total * line.amount) * 0.01

            rec.total = total_per + total_amt
            print('total=', rec.total)

    def action_confirm(self):
        self.state = 'confirm'
        for line in self.line_ids:
            if line.invoices_id:
                line.invoices_id.broker_id = self.partner_id.id
                line.invoices_id.deal_type = line.deal_type
                line.invoices_id.rate = line.amount
                print(f'Updated Invoice: {line.invoices_id.name} with broker: {self.partner_id.name}')

        names = ', '.join(line.invoices_id.name for line in self.line_ids if line.invoices_id)
        res = self.env['account.move'].create({
            'date': date.today(),
            'journal_id': 3,
            'broker_id': self.partner_id.id,
            'ref': names,
            'move_type': 'entry',
            'line_ids': [(0, 0, {
                'account_id': self.env['account.account'].search([('name', '=', 'Product Sales')], limit=1).id,
                'partner_id': self.partner_id.id,
                'debit': self.total,
                'credit': 0,
            }), (0, 0, {
                'account_id': self.env['account.account'].search([('name', '=', 'broker')], limit=1).id,
                'partner_id': self.partner_id.id,
                'debit': 0,
                'credit': self.total,
            })]
        })
        self.journal_entry_id = res.id
        print('journal_entries= ', res.ref)
        res.action_post()
        return res

    def action_draft(self):
        self.state = 'draft'
        if self.journal_entry_id:
            self.journal_entry_id.button_draft()
            self.journal_entry_id.unlink()
            self.journal_entry_id = False


class BrokerLine(models.Model):
    _name = 'broker.line'
    invoices_id = fields.Many2one('account.move', required=1)
    broker_id = fields.Many2one('broker')
    customer = fields.Char(related='invoices_id.partner_id.name', string='Customer')
    total = fields.Monetary(readonly=True, compute="_compute_total")
    currency_id = fields.Many2one('res.currency', related='invoices_id.currency_id', readonly=True)
    deal_type = fields.Selection(selection=[
        ('perc', 'Percentage'),
        ('amt', 'Amount'),
    ])
    amount = fields.Integer()

    @api.depends('invoices_id.line_ids.price_subtotal')
    def _compute_total(self):
        for rec in self:
            rec.total = sum(line.price_subtotal for line in rec.invoices_id.line_ids)

    # @api.onchange('deal_type', 'total')
    # def _onchange_deal_type(self):
    #     if self.deal_type == 'perc' and self.total:
    #         self.amount = int(self.total * self.amount_per)
