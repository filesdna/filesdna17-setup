from odoo import models, fields, api


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    product_id = fields.Many2one('product.product')
    sale_line_id = fields.Many2one('sale.order.line')
    price_unit = fields.Float(compute='_compute_price')
    balance = fields.Float(compute='_compute_balance')

    @api.depends('product_id')
    def _compute_price(self):
        for record in self:
            record.price_unit = record.stock_move_id.sale_line_id.price_unit
            print('price_unit=', record.stock_move_id.sale_line_id.price_unit)

    @api.depends('product_id', 'quantity', 'price_unit')
    def _compute_balance(self):
        sorted_records = sorted(self, key=lambda rec: rec.create_date)
        product_quantities = {}
        for rec in sorted_records:
            if rec.product_id:
                if rec.product_id.id in product_quantities:
                    product_quantities[rec.product_id.id] += rec.quantity
                else:
                    product_quantities[rec.product_id.id] = rec.quantity
                rec.balance = product_quantities.get(rec.product_id.id, 0)
                print('Processing record:', rec.id)
                print('Product Template:', rec.product_tmpl_id.name)
                print('Balance=', rec.balance)
                print('==================================================================')
