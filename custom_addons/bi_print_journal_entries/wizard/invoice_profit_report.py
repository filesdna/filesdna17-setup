from odoo import fields, models, api
from odoo.exceptions import ValidationError
from datetime import date


class SalesDetails(models.Model):
    _name = 'sale.details'

    date_from = fields.Date(default=lambda self: self._get_first_day_of_current_month())
    date_to = fields.Date(default=fields.Date.context_today, )
    invoice_type = fields.Selection([
        ('customer_invoice', 'Customer Invoice'),
        ('vendor_bill', 'Vendor Bill'),
    ])
    report_print_by = fields.Selection([
        ('customers', 'Customers'),
        ('product', 'Product'),
        ('customer_with_product', 'Customer With Product'),
        ('invoices', 'Invoices'),

    ])
    product_id = fields.Many2many('product.product',
                                  help='If You Select Product In "Report Print By" And Set The Product Empty You Can See All Product,,,')
    partner_id = fields.Many2many('res.partner', string='Contact')
    company_id = fields.Many2one('res.company', string='Companies', default=lambda self: self.env.user.company_id.id,
                                 )
    sale_id = fields.Many2many('sale.order')
    sale_ref = fields.Many2one('sale.order', string='Invoices')
    profit = fields.Float(_compute='_compute_profit')
    margin = fields.Float(_compute='_compute_margin', digits=(6, 2))

    @api.model
    def _get_first_day_of_current_month(self):
        today = date.today()
        return date(today.year, today.month, 1)

    @api.depends('rec.product_id.standard_price', 'rec.product_id.price_unit')
    def _compute_profit(self):
        for rec in self:
            print('cost=', rec.product_id.standard_price)
            print('sale price=', rec.product_id.price_unit)
            rec.profit = rec.product_id.standard_price - rec.product_id.price_unit

    @api.depends('profit', 'rec.product_id.price_unit')
    def _compute_margin(self):
        for rec in self:
            rec.margin = rec.profit - rec.product_id.standard_price

    def action_confirm(self):
        print("action confirm")
        cost = []

        if not self.date_from or not self.date_to:
            raise ValidationError("Add The Date From And The Date To")

        sale_orders = self.env['sale.order'].search([
            ('date_order', '>=', self.date_from),
            ('date_order', '<=', self.date_to)
        ])
        if self.invoice_type == 'customer_invoice':
            if sale_orders:
                for res in sale_orders:
                    order_lines_dict = {}
                    for line in res.order_line:
                        product_id = line.product_id.id
                        if product_id in order_lines_dict:
                            order_lines_dict[product_id]['product_uom_qty'] += line.product_uom_qty
                            order_lines_dict[product_id]['price_subtotal'] += line.price_subtotal
                            order_lines_dict[product_id][
                                'standard_price'] += line.product_id.standard_price * line.product_uom_qty
                            order_lines_dict[product_id]['profit'] = order_lines_dict[product_id]['price_subtotal'] - \
                                                                     order_lines_dict[product_id]['standard_price']
                            if order_lines_dict[product_id]['price_subtotal'] > 0:
                                order_lines_dict[product_id]['margin'] = order_lines_dict[product_id]['profit'] / \
                                                                         order_lines_dict[product_id][
                                                                             'price_subtotal'] * 100
                            else:
                                order_lines_dict[product_id]['margin'] = 0
                        else:
                            price_subtotal = line.price_subtotal
                            standard_price = line.product_id.standard_price * line.product_uom_qty
                            profit = price_subtotal - standard_price
                            order_lines_dict[product_id] = {
                                'product_id': line.product_id.name,
                                'product_uom_qty': line.product_uom_qty,
                                'product_uom': line.product_uom.name,
                                'price_subtotal': price_subtotal,
                                'standard_price': standard_price,
                                'profit': profit,
                                'margin': ((
                                                   price_subtotal - standard_price) / price_subtotal * 100) if price_subtotal > 0 else 0
                            }
                    cost.append({
                        'sale_id': res.name,
                        'partner_id': res.partner_id.name,
                        'date_order': res.date_order.strftime('%Y-%m-%d'),
                        'order_lines': list(order_lines_dict.values()),
                    })
                return {
                    'type': 'ir.actions.report',
                    'report_name': 'bi_print_journal_entries.invoice_profit_report_template',
                    'report_type': 'qweb-pdf',
                    'context': {'active_ids': self.ids},
                    'data': {'cost': cost},
                }
            else:
                raise ValidationError("Don't Have Sales In This Dates for Customer")

        elif self.invoice_type == 'vendor_bill':
            cost = []
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

                        })
                    cost.append({
                        'purchase_id': res.name,
                        'partner_id': res.partner_id.name,
                        'date_planned': res.date_planned,
                        'order_lines': order_lines,
                    })

                return {
                    'type': 'ir.actions.report',
                    'report_name': 'bi_print_journal_entries.purchase_report_template',
                    'report_type': 'qweb-pdf',
                    'context': {'active_ids': self.ids},
                    'data': {'cost': cost},
                }
            else:
                raise ValidationError("Dont Have Purchase In This Dates")

        elif self.report_print_by == 'product':
            cost = []
            if self.product_id:
                products_to_check = self.product_id
            else:
                products_to_check = self.env['product.product'].search([])
            for product in products_to_check:
                sale_orders = self.env['sale.order.line'].search([
                    ('product_id', '=', product.id),
                ])
                print('pro=', sale_orders.mapped('name'))
                if sale_orders:
                    order_data = {}
                    for res in sale_orders:
                        order = res.order_id
                        if order.id not in order_data:
                            order_data[order.id] = {
                                'sale_id': order.name,
                                'partner_id': order.partner_id.name,
                                'date_order': order.date_order.strftime('%Y-%m-%d'),
                                'order_lines': []
                            }
                        product_found = False
                        for line in order_data[order.id]['order_lines']:
                            if line['product_id'] == res.product_id.name:
                                line['product_uom_qty'] += res.product_uom_qty
                                line['price_subtotal'] += res.price_subtotal
                                line['standard_price'] += res.product_id.standard_price * res.product_uom_qty
                                line['profit'] = line['price_subtotal'] - line['standard_price']
                                if line['price_subtotal'] > 0:
                                    line['margin'] = (line['profit'] / line['price_subtotal'] * 100)
                                else:
                                    line['margin'] = 0
                                product_found = True
                                break
                        if not product_found:
                            price_subtotal = res.price_subtotal
                            standard_price = res.product_id.standard_price * res.product_uom_qty
                            profit = price_subtotal - standard_price
                            order_data[order.id]['order_lines'].append({
                                'product_id': res.product_id.name,
                                'product_uom_qty': res.product_uom_qty,
                                'product_uom': res.product_uom.name,
                                'price_subtotal': price_subtotal,
                                'standard_price': standard_price,
                                'profit': profit,
                                'margin': ((
                                                   price_subtotal - standard_price) / price_subtotal * 100) if price_subtotal > 0 else 0
                            })
                    cost.extend(order_data.values())
            if cost:
                return {
                    'type': 'ir.actions.report',
                    'report_name': 'bi_print_journal_entries.product_report_template',
                    'report_type': 'qweb-pdf',
                    'context': {'active_ids': self.ids},
                    'data': {'cost': cost},
                }
            else:
                raise ValidationError("Don't have sales in these dates")

        elif self.report_print_by == 'customers':
            if not self.partner_id:
                raise ValidationError("Add The Contact")
            cost = []

            for partner in self.partner_id:
                sale_orders = self.env['sale.order'].search([
                    ('partner_id', '=', partner.id),
                    ('date_order', '>=', self.date_from),
                    ('date_order', '<=', self.date_to),
                ])
                if sale_orders:
                    for res in sale_orders:
                        order_lines_dict = {}
                        for line in res.order_line:
                            product_id = line.product_id.id
                            if product_id in order_lines_dict:
                                order_lines_dict[product_id]['product_uom_qty'] += line.product_uom_qty
                                order_lines_dict[product_id]['price_subtotal'] += line.price_subtotal
                                order_lines_dict[product_id][
                                    'standard_price'] += line.product_id.standard_price * line.product_uom_qty
                                order_lines_dict[product_id]['profit'] = order_lines_dict[product_id][
                                                                             'price_subtotal'] - \
                                                                         order_lines_dict[product_id][
                                                                             'standard_price']
                                if order_lines_dict[product_id]['price_subtotal'] > 0:
                                    order_lines_dict[product_id]['margin'] = order_lines_dict[product_id]['profit'] / \
                                                                             order_lines_dict[product_id][
                                                                                 'price_subtotal'] * 100
                                else:
                                    order_lines_dict[product_id]['margin'] = 0
                            else:
                                price_subtotal = line.price_subtotal
                                standard_price = line.product_id.standard_price * line.product_uom_qty
                                profit = price_subtotal - standard_price
                                order_lines_dict[product_id] = {
                                    'product_id': line.product_id.name,
                                    'product_uom_qty': line.product_uom_qty,
                                    'product_uom': line.product_uom.name,
                                    'price_subtotal': price_subtotal,
                                    'standard_price': standard_price,
                                    'profit': profit,
                                    'margin': ((
                                                       price_subtotal - standard_price) / price_subtotal * 100) if price_subtotal > 0 else 0
                                }
                        order_lines = list(order_lines_dict.values())
                        cost.append({
                            'sale_id': res.name,
                            'partner_id': res.partner_id.name,
                            'date_order': res.date_order.strftime('%Y-%m-%d'),
                            'order_lines': order_lines,
                        })

                else:
                    raise ValidationError(f"Don't Have Sales In This Dates for Customer {partner.name}")
            if cost:
                return {
                    'type': 'ir.actions.report',
                    'report_name': 'bi_print_journal_entries.customer_report_template',
                    'report_type': 'qweb-html',
                    'context': {'active_ids': self.ids},
                    'data': {'cost': cost},
                }
            else:
                raise ValidationError("Dont Have Sales In This Dates")

        elif self.report_print_by == 'customer_with_product':

            cost = []

            if not self.partner_id:
                raise ValidationError("Please add a contact.")

            if not self.product_id:
                raise ValidationError("Please add a product.")

            for partner in self.partner_id:
                sale_orders = self.env['sale.order'].search([
                    ('partner_id', '=', partner.id),
                    ('order_line.product_id', 'in', self.product_id.ids),
                ])
                for order in sale_orders:
                    order_lines = {}
                    for line in order.order_line:
                        if line.product_id.id in self.product_id.ids:
                            if line.product_id.id not in order_lines:
                                price_subtotal = line.price_subtotal
                                standard_price = line.product_id.standard_price * line.product_uom_qty
                                profit = price_subtotal - standard_price
                                order_lines[line.product_id.id] = {
                                    'product_id': line.product_id.name,
                                    'product_uom_qty': line.product_uom_qty,
                                    'product_uom': line.product_uom.name,
                                    'price_subtotal': price_subtotal,
                                    'standard_price': standard_price,
                                    'profit': profit,
                                    'margin': (
                                        (price_subtotal - standard_price) / price_subtotal * 100
                                        if line.price_subtotal > 0 else 0)
                                }
                            else:
                                order_lines[line.product_id.id]['product_uom_qty'] += line.product_uom_qty
                                order_lines[line.product_id.id]['price_subtotal'] += line.price_subtotal
                                order_lines[line.product_id.id][
                                    'standard_price'] += line.product_id.standard_price * line.product_uom_qty
                                order_lines[line.product_id.id]['profit'] = order_lines[line.product_id.id][
                                                                                'price_subtotal'] - \
                                                                            order_lines[line.product_id.id][
                                                                                'standard_price']
                                order_lines[line.product_id.id]['margin'] = (
                                    order_lines[line.product_id.id]['profit'] / order_lines[line.product_id.id][
                                        'price_subtotal'] * 100
                                    if order_lines[line.product_id.id]['price_subtotal'] > 0 else 0)
                    if order_lines:
                        cost.append({
                            'sale_id': order.name,
                            'partner_id': partner.name,
                            'date_order': order.date_order.strftime('%Y-%m-%d'),
                            'order_lines': list(order_lines.values()),
                        })
            return {
                'type': 'ir.actions.report',
                'report_name': 'bi_print_journal_entries.customer_product_report_template',
                'report_type': 'qweb-html',
                'context': {'active_ids': self.ids},
                'data': {'cost': cost},
            }
        elif self.report_print_by == 'invoices':
            if self.sale_ref:
                ref_to_check = self.sale_ref
            else:
                ref_to_check = self.env['sale.order'].search([])
            cost = []
            for ref in ref_to_check:
                sale_orders = self.env['sale.order'].search([
                    ('id', '=', ref.id),
                ])
                if sale_orders:
                    order_data = {}
                    for res in sale_orders:
                        order = res
                        if order.id not in order_data:
                            order_data[order.id] = {
                                'sale_id': order.name,
                                'partner_id': order.partner_id.name,
                                'date_order': order.date_order.strftime('%Y-%m-%d'),
                                'order_lines': []
                            }
                        for line in order.order_line:
                            existing_product = next((item for item in order_data[order.id]['order_lines'] if
                                                     item['product_id'] == line.product_id.name), None)
                            if existing_product:
                                existing_product['product_uom_qty'] += line.product_uom_qty
                                existing_product['price_subtotal'] += line.price_subtotal
                                existing_product[
                                    'standard_price'] += line.product_id.standard_price * line.product_uom_qty
                                existing_product['profit'] = existing_product['price_subtotal'] - existing_product[
                                    'standard_price']
                                if existing_product['price_subtotal'] > 0:
                                    existing_product['margin'] = existing_product['profit'] / existing_product[
                                        'price_subtotal'] * 100
                                else:
                                    existing_product['margin'] = 0
                            else:
                                price_subtotal = line.price_subtotal
                                standard_price = line.product_id.standard_price * line.product_uom_qty
                                profit = price_subtotal - standard_price
                                order_data[order.id]['order_lines'].append({
                                    'product_id': line.product_id.name,
                                    'product_uom_qty': line.product_uom_qty,
                                    'product_uom': line.product_uom.name,
                                    'price_subtotal': price_subtotal,
                                    'standard_price': standard_price,
                                    'profit': profit,
                                    'margin': ((
                                                       price_subtotal - standard_price) / price_subtotal * 100) if price_subtotal > 0 else 0

                                })
                    cost.extend(order_data.values())
            if cost:
                return {
                    'type': 'ir.actions.report',
                    'report_name': 'bi_print_journal_entries.reference_report_template',
                    'report_type': 'qweb-html',
                    'context': {'active_ids': self.ids},
                    'data': {'cost': cost},
                }
            else:
                raise ValidationError("Dont Have Sales In This Dates")

        elif not self.partner_id:
            raise ValidationError("Add The Contacts")

        cost = []
        for partner in self.partner_id:
            sale_orders = self.env['sale.order'].search([
                ('partner_id', '=', partner.id),
            ])
            if sale_orders:
                for res in sale_orders:
                    order_lines_dict = {}
                    for line in res.order_line:
                        product_id = line.product_id.id
                        if product_id in order_lines_dict:
                            order_lines_dict[product_id]['product_uom_qty'] += line.product_uom_qty
                            order_lines_dict[product_id]['price_subtotal'] += line.price_subtotal
                            order_lines_dict[product_id][
                                'standard_price'] += line.product_id.standard_price * line.product_uom_qty
                            order_lines_dict[product_id]['profit'] = order_lines_dict[product_id]['price_subtotal'] - \
                                                                     order_lines_dict[product_id]['standard_price']
                            if order_lines_dict[product_id]['price_subtotal'] > 0:
                                order_lines_dict[product_id]['margin'] = order_lines_dict[product_id]['profit'] / \
                                                                         order_lines_dict[product_id][
                                                                             'price_subtotal'] * 100
                            else:
                                order_lines_dict[product_id]['margin'] = 0
                        else:
                            price_subtotal = line.price_subtotal
                            standard_price = line.product_id.standard_price * line.product_uom_qty
                            profit = price_subtotal - standard_price
                            order_lines_dict[product_id] = {
                                'product_id': line.product_id.name,
                                'product_uom_qty': line.product_uom_qty,
                                'product_uom': line.product_uom.name,
                                'price_subtotal': price_subtotal,
                                'standard_price': standard_price,
                                'profit': profit,
                                'margin': ((
                                                   price_subtotal - standard_price) / price_subtotal * 100) if price_subtotal > 0 else 0
                            }
                    order_lines = list(order_lines_dict.values())
                    cost.append({
                        'sale_id': res.name,
                        'partner_id': res.partner_id.name,
                        'date_order': res.date_order.strftime('%Y-%m-%d'),
                        'order_lines': order_lines,
                    })

            else:
                raise ValidationError(f"Don't Have Sales In This Dates for Customer {partner.name}")

            return {
                'type': 'ir.actions.report',
                'report_name': 'bi_print_journal_entries.invoice_profit_report_template',
                'report_type': 'qweb-pdf',
                'context': {'active_ids': self.ids},
                'data': {'cost': cost},
            }
