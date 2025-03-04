from odoo import fields, models, api
from datetime import date
from odoo.exceptions import ValidationError


class VatInputOutput(models.Model):
    _name = 'vat.input.output'

    date_from = fields.Date(default=lambda self: self._get_first_day_of_current_month())
    date_to = fields.Date(default=fields.Date.context_today)
    type = fields.Selection([
        ('sales', 'Sales'),
        ('purchase', 'Purchase'),
    ])

    @api.model
    def _get_first_day_of_current_month(self):
        today = date.today()
        return date(today.year, today.month, 1)

    def action_confirm(self):
        print("action confirm")
        cost = []
        order_lines = []
        if not self.date_from or not self.date_to:
            raise ValidationError("Add The Date From And The Date To")
        if self.type == 'sales':
            account_move_line_in = self.env['account.move.line'].search([
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('parent_state', '=', 'posted'),
                ('account_id.name', 'in', ['VAT Input']),
            ])

            print('account_move_line_in=', account_move_line_in)
            if account_move_line_in:
                for res in account_move_line_in:
                    order_lines.append({
                        'account_id': res.account_id.name,
                        'partner_id': res.partner_id.name,
                        'name': res.name,
                        'debit': res.debit,
                        'credit': res.credit,
                        'balance': res.balance,
                    })
                    print('order_lines=', order_lines)
                cost.append({
                    'order_lines': order_lines,
                })
            return {
                'type': 'ir.actions.report',
                'report_name': 'task_vat_input_output.vat_input_output_report_template',
                'report_type': 'qweb-html',
                'context': {'active_ids': self.ids},
                'data': {'cost': cost},
            }

        elif self.type == 'purchase':
            account_move_line_out = self.env['account.move.line'].search([
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('parent_state', '=', 'posted'),
                ('account_id.name', 'in', ['VAT Output']),
            ])

            print('account_move_line_out=', account_move_line_out)
            if account_move_line_out:
                for res in account_move_line_out:
                    order_lines.append({
                        'account_id': res.account_id.name,
                        'partner_id': res.partner_id.name,
                        'name': res.name,
                        'debit': res.debit,
                        'credit': res.credit,
                        'balance': res.balance,
                    })
                    print('order_lines=', order_lines)
                cost.append({
                    'order_lines': order_lines,
                })

            return {
                'type': 'ir.actions.report',
                'report_name': 'task_vat_input_output.vat_input_output_report_template',
                'report_type': 'qweb-html',
                'context': {'active_ids': self.ids},
                'data': {'cost': cost},
            }
        elif self.type == False:
            account_move_line = self.env['account.move.line'].search([
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('account_id.name', 'in', ['Tax Paid', 'Tax Received']),
            ])

            print('account_move_line_out=', account_move_line)
            if account_move_line:
                for res in account_move_line:
                    order_lines.append({
                        'account_id': res.account_id.name,
                        'partner_id': res.partner_id.name,
                        'name': res.name,
                        'debit': res.debit,
                        'credit': res.credit,
                        'balance': res.balance,
                    })
                    print('order_lines=', order_lines)
                cost.append({
                    'order_lines': order_lines,
                })

            return {
                'type': 'ir.actions.report',
                'report_name': 'task_vat_input_output.vat_input_output_report_template',
                'report_type': 'qweb-html',
                'context': {'active_ids': self.ids},
                'data': {'cost': cost},
            }
        else:
            raise ValidationError("Don't Have Data In This Dates")
