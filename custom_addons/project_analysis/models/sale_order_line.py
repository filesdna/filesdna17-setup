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

    invoice_status = fields.Selection([
        ('no', 'No Invoice'),
        ('to invoice', 'To Invoice'),
        ('invoiced', 'Fully Invoiced'),
        ('partially invoiced', 'Partially Invoiced'),
    ], string="Invoice Status", store=True, readonly=True, compute="_compute_invoice_status")

    @api.depends('qty_invoiced', 'qty_delivered', 'product_uom_qty', 'order_id.invoice_ids')
    def _compute_invoice_status(self):
        for line in self:
            total_invoiced = sum(line.order_id.invoice_ids.mapped('amount_total'))
            total_order = sum(line.order_id.order_line.mapped('price_subtotal'))

            if total_invoiced >= total_order:
                line.invoice_status = 'invoiced'
            elif total_invoiced > 0:
                line.invoice_status = 'partially invoiced'
            elif line.qty_delivered > 0:
                line.invoice_status = 'to invoice'
            else:
                line.invoice_status = 'no'

            print(f"[DEBUG] Line {line.name} Invoice Status Updated: {line.invoice_status}")

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
