from odoo import fields, models, api

class SaleOrderLineImage(models.Model):
    _inherit = 'sale.order.line'

    product_image = fields.Binary(
        string="Product Image",
        store=True
    )

    @api.onchange('product_id')
    def onchange_sale_product_image(self):
    	for product in self:
    		product.product_image = product.product_id.image_128


class SaleOrderProject(models.Model):
    _inherit = 'sale.order'

    locked = fields.Boolean(default=False, copy=False, help="Locked orders cannot be modified.")
    project_id = fields.Many2one(comodel_name='project.project', string='Project Code')
    

class PurchaseOrderProject(models.Model):
    _inherit = 'purchase.order'

    project_id = fields.Many2one(comodel_name='project.project', string='Project Code')

class PyrchaseOrderLineImage(models.Model):
    _inherit = 'purchase.order.line'

    product_image = fields.Binary(
        string="Product Image"
    )