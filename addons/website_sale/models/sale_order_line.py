# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    linked_line_id = fields.Many2one('sale.order.line', string='Linked Order Line', domain="[('order_id', '=', order_id)]", ondelete='cascade', copy=False, index=True)
    option_line_ids = fields.One2many('sale.order.line', 'linked_line_id', string='Options Linked')

    name_short = fields.Char(compute="_compute_name_short")

    shop_warning = fields.Char('Warning')

    #=== COMPUTE METHODS ===#

    @api.depends('linked_line_id', 'option_line_ids')
    def _compute_name(self):
        """Override to add the compute dependency.

        The custom name logic can be found below in _get_sale_order_line_multiline_description_sale.
        """
        super()._compute_name()

    @api.depends('product_id.display_name')
    def _compute_name_short(self):
        """ Compute a short name for this sale order line, to be used on the website where we don't have much space.
            To keep it short, instead of using the first line of the description, we take the product name without the internal reference.
        """
        for record in self:
            record.name_short = record.product_id.with_context(display_default_code=False).display_name

    #=== BUSINESS METHODS ===#

    def _get_sale_order_line_multiline_description_sale(self):
        description = super()._get_sale_order_line_multiline_description_sale()
        if self.linked_line_id:
            description += "\n" + _("Option for: %s", self.linked_line_id.product_id.display_name)
        if self.option_line_ids:
            description += "\n" + '\n'.join([
                _("Option: %s", option_line.product_id.display_name)
                for option_line in self.option_line_ids
            ])
        return description

    def get_description_following_lines(self):
        return self.name.splitlines()[1:]

    def _get_order_date(self):
        self.ensure_one()
        if self.order_id.website_id and self.state == 'draft':
            # cart prices must always be computed based on the current time, not on the order
            # creation date.
            return fields.Datetime.now()
        return super()._get_order_date()

    def _get_pricelist_price_before_discount(self):
        """On ecommerce orders, the base price must always be the sales price."""
        self.ensure_one()
        self.product_id.ensure_one()

        if self.order_id.website_id:
            return self.env['product.pricelist.item']._compute_price_before_discount(
                product=self.product_id.with_context(**self._get_product_price_context()),
                quantity=self.product_uom_qty or 1.0,
                uom=self.product_uom,
                date=self._get_order_date(),
                currency=self.currency_id,
            )

        return super()._get_pricelist_price_before_discount()

    def _get_shop_warning(self, clear=True):
        self.ensure_one()
        warn = self.shop_warning
        if clear:
            self.shop_warning = ''
        return warn

    def _get_displayed_unit_price(self):
        show_tax = self.order_id.website_id.show_line_subtotals_tax_selection
        tax_display = 'total_excluded' if show_tax == 'tax_excluded' else 'total_included'

        return self.tax_id.compute_all(
            self.price_unit, self.currency_id, 1, self.product_id, self.order_partner_id,
        )[tax_display]

    def _get_displayed_quantity(self):
        rounded_uom_qty = round(self.product_uom_qty,
                                self.env['decimal.precision'].precision_get('Product Unit of Measure'))
        return int(rounded_uom_qty) == rounded_uom_qty and int(rounded_uom_qty) or rounded_uom_qty

    def _show_in_cart(self):
        self.ensure_one()
        # Exclude delivery & section/note lines from showing up in the cart
        return not self.is_delivery and not bool(self.display_type)

    def _is_reorder_allowed(self):
        self.ensure_one()
        return self.product_id._is_add_to_cart_allowed()
