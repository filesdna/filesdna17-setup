from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    _name = "sale.order.line"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    price_unit = fields.Float(
        string="Unit Price",
        tracking=True  # Enables automatic tracking in chatter
    )

    sale_order_id = fields.Many2one(
        'sale.order',
        string="Related Sale Order",
        related="order_id.sale_order_id",
        store=True
    )

    product_uom_qty = fields.Float(
        string="Quantity",
        tracking=True  # Enables automatic tracking in chatter
    )

    def write(self, vals):
        for record in self:
            changes = []

            # Track Price Changes
            if 'price_unit' in vals:
                old_price = record.price_unit
                new_price = vals['price_unit']
                changes.append(f"Price changed from {old_price} to {new_price}")

            # Track Quantity Changes
            if 'product_uom_qty' in vals:
                old_qty = record.product_uom_qty
                new_qty = vals['product_uom_qty']
                changes.append(f"Quantity changed from {old_qty} to {new_qty}")

            if changes:
                message = "Updated: " + ", ".join(changes)
                record.order_id.message_post(body=message)

        return super(SaleOrderLine, self).write(vals)
