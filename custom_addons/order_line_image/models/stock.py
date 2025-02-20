from odoo import fields, models, api


class StockMoveSaleLine(models.Model):
    _inherit = 'stock.move'

    product_image = fields.Binary(
        string="Product Image",
        related='sale_line_id.product_image',
        readonly=True,
        store=True
    )

    description = fields.Text(
        string='Description', 
        related='sale_line_id.name',
        readonly=True,
        store=True
    )
           
class StockMoveLineSaleLine(models.Model):
    _inherit = 'stock.move.line'

    product_image = fields.Binary(
        string="Product Image",
        related='move_id.product_image',
        readonly=True,
        store=True
    )

    description = fields.Text(
        string='Description', 
        related='move_id.description',
        readonly=True,
        store=True
    )