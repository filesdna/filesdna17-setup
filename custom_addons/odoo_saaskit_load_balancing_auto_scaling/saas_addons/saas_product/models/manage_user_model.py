from odoo import api, fields, models, _
from odoo.exceptions import UserError


# Commented for no use in present
# class user_aro(models.Model):
#     _name = 'user.add.remove'
#     _description = 'User Add Remove'
#
#     tenant_id = fields.Many2one('tenant.database.list')
#     total_users = fields.Integer()
#     new_users = fields.Integer()
#     log_date = fields.Date()
#     type = fields.Selection([('add', 'Add'), ('remove', 'Remove')], default='add')


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_is_package(self):
        # print('\n\n_____________Package : ', self.is_package)
        if self.is_package:
            return True
        else:
            return False

    def get_list_price(self, partner=None):
        if self.env.context.get('website_id'):
            current_website = self.env['website'].get_current_website()
            pricelist = current_website._get_current_pricelist()
            order_id = current_website.sale_get_order()
            # print('current invoicing term \n\n\n\n\n:', order_id.invoice_term_id)
            if(order_id.invoice_term_id.name == 'Yearly'):
                prod_price = self.with_context(quantity=12, pricelist=pricelist.id).lst_price
            else:
                prod_price = self.with_context(pricelist=pricelist.id).lst_price

            return round(prod_price, 2)
        else:
            if partner:
                pricelist = partner.property_product_pricelist
                prod_price = self.with_context(pricelist=pricelist.id).lst_price
                print('\n\nComputed Price for Product for invoice : \n\n{}'.format(prod_price))
            else:
                prod_price = self.lst_price
            return round(prod_price, 2)

    def get_list_currency(self):
        if self.env.context.get('website_id'):
            current_website = self.env['website'].get_current_website()
            pricelist = current_website._get_current_pricelist()

            return pricelist.currency_id.name if pricelist else self.currency_id.name
        else:
            return self.currency_id.name
