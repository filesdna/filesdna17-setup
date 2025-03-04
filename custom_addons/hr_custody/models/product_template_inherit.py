from odoo import models, fields, api
import logging


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_custody = fields.Boolean(string='Can be Custody')
    custody_property = fields.One2many('custody.property', 'product_template_id')
    property_state = fields.Selection(related='custody_property.state', store=True)

    def get_products_in_custody(self):
        products = self.search([('custody_property', '!=', False)])
        return products