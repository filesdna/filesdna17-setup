from odoo import fields, models
from odoo.exceptions import ValidationError
from odoo.exceptions import ValidationError
from datetime import datetime


class PurchaseDetails(models.Model):
    _name = 'purchase.details'

    date_from = fields.Date()
    date_to = fields.Date()
    purchase_id = fields.Many2many('purchase.order')

    def action_confirm(self):
        print("action_confirm")
        cost = []

        if not self.date_from or not self.date_to:
            raise ValidationError("Add The Date From And The Date To")

        purchase_orders = self.env['purchase.order'].search([
            ('date_order', '>=', self.date_from),
            ('date_order', '<=', self.date_to)
        ])
        if purchase_orders:
            for res in purchase_orders:
                order_lines = []
                for line in res.order_line:
                    order_lines.append({
                        'product_id': line.product_id.name,
                        'name': line.name,
                        'product_qty': line.product_qty,
                        'product_uom': line.product_uom.name,
                        'price_unit': line.price_unit,
                        'taxes_id': line.taxes_id.name,
                        'price_subtotal': line.price_subtotal,
                        'profit': line.product_id.standard_price - line.price_unit,

                    })
                cost.append({
                    'purchase_id': res.name,
                    'partner_id': res.partner_id.name,
                    'date_planned': res.date_planned,
                    'order_lines': order_lines,
                })

            return {
                'type': 'ir.actions.report',
                'report_name': 'Task_Desktop.purchase_report_template',
                'report_type': 'qweb-html',
                'context': {'active_ids': self.ids},
                'data': {'cost': cost},
            }
        else:
            raise ValidationError("Dont Have Purchase In This Dates")