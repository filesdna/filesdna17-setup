from odoo import models, fields


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        """Override the confirm method to update invoice status in sale order"""
        res = super(AccountMove, self).action_post()

        for move in self:
            if move.move_type == "out_invoice" and move.invoice_origin:
                sale_order = self.env["sale.order"].search([("name", "=", move.invoice_origin)], limit=1)
                if sale_order:
                    # Check total invoiced amount
                    total_invoiced = sum(
                        sale_order.invoice_ids.filtered(lambda inv: inv.state == "posted").mapped("amount_total"))

                    if total_invoiced >= sale_order.amount_total:
                        sale_order.invoice_status = "invoiced"  # Fully invoiced
                    else:
                        sale_order.invoice_status = "partially invoiced"  # Partially invoiced

        return res
