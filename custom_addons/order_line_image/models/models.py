from odoo import fields, models, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_image = fields.Binary(
        string="Product Image", 
        related='product_id.image_1920', 
        readonly=True
    )




class SaleOrderLine(models.Model):
    _inherit = 'sale.order'

    locked = fields.Boolean(default=False, copy=False, help="Locked orders cannot be modified.")
