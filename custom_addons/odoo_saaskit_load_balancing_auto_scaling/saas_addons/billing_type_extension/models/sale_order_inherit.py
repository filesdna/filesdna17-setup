from odoo import fields, models, api,_
from odoo.tools.float_utils import float_round as round
from odoo.http import request
from odoo.exceptions import UserError,ValidationError
import logging

_logger = logging.getLogger(__name__)


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'


    def _prepare_invoice(self):
        invoice_vals = super(SaleOrderInherit, self)._prepare_invoice()
        invoice_vals['billing'] = self.billing

        # print("invoice valsssssssssssssssssssssssss\n",invoice_vals)
        return invoice_vals

    # def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
    #     """ Add or set product quantity, add_qty can be negative """
    #     print('\n\n\nasdfsalkfdsfsfsdfsdfsd_____________________________', add_qty, set_qty, kwargs, product_id, line_id)
    #     self.ensure_one()
    #     product_context = dict(self.env.context)
    #     product_context.setdefault('lang', self.sudo().partner_id.lang)
    #     SaleOrderLineSudo = self.env['sale.order.line'].sudo().with_context(product_context)
    #     # change lang to get correct name of attributes/values
    #     product_with_context = self.env['product.product'].with_context(product_context)
    #     product = product_with_context.browse(int(product_id))
    #
    #     try:
    #         if add_qty:
    #             add_qty = int(add_qty)
    #     except ValueError:
    #         add_qty = 1
    #
    #     try:
    #         if set_qty:
    #             set_qty = int(set_qty)
    #     except ValueError:
    #         set_qty = 0
    #
    #     quantity = 0
    #     order_line = False
    #     if self.state != 'draft':
    #         request.session['sale_order_id'] = None
    #         raise UserError(_('It is forbidden to modify a sales order which is not in draft status.'))
    #
    #     if line_id is not False:
    #         order_line = self._cart_find_product_line(product_id, line_id, **kwargs)[:1]
    #
    #     # Create line if no line with product_id can be located
    #     if not order_line:
    #         if not product:
    #             raise UserError(_("The given product does not exist therefore it cannot be added to cart."))
    #
    #         no_variant_attribute_values = kwargs.get('no_variant_attribute_values') or []
    #         received_no_variant_values = product.env['product.template.attribute.value'].browse([int(ptav['value']) for ptav in no_variant_attribute_values])
    #         received_combination = product.product_template_attribute_value_ids | received_no_variant_values
    #         product_template = product.product_tmpl_id
    #
    #         # handle all cases where incorrect or incomplete data are received
    #         combination = product_template._get_closest_possible_combination(received_combination)
    #
    #         # get or create (if dynamic) the correct variant
    #         product = product_template._create_product_variant(combination)
    #
    #         if not product:
    #             raise UserError(_("The given combination does not exist therefore it cannot be added to cart."))
    #
    #         product_id = product.id
    #
    #         values = self._website_product_id_change(self.id, product_id, qty=1)
    #
    #         # add no_variant attributes that were not received
    #         for ptav in combination.filtered(lambda ptav: ptav.attribute_id.create_variant == 'no_variant' and ptav not in received_no_variant_values):
    #             no_variant_attribute_values.append({
    #                 'value': ptav.id,
    #             })
    #
    #         # save no_variant attributes values
    #         if no_variant_attribute_values:
    #             values['product_no_variant_attribute_value_ids'] = [
    #                 (6, 0, [int(attribute['value']) for attribute in no_variant_attribute_values])
    #             ]
    #
    #         # add is_custom attribute values that were not received
    #         custom_values = kwargs.get('product_custom_attribute_values') or []
    #         received_custom_values = product.env['product.template.attribute.value'].browse([int(ptav['custom_product_template_attribute_value_id']) for ptav in custom_values])
    #
    #         for ptav in combination.filtered(lambda ptav: ptav.is_custom and ptav not in received_custom_values):
    #             custom_values.append({
    #                 'custom_product_template_attribute_value_id': ptav.id,
    #                 'custom_value': '',
    #             })
    #
    #         # save is_custom attributes values
    #         if custom_values:
    #             values['product_custom_attribute_value_ids'] = [(0, 0, {
    #                 'custom_product_template_attribute_value_id': custom_value['custom_product_template_attribute_value_id'],
    #                 'custom_value': custom_value['custom_value']
    #             }) for custom_value in custom_values]
    #
    #         # create the line
    #         # print("\n\ncreate_order_line____________ : ", values)
    #         order_line = SaleOrderLineSudo.create(values)
    #
    #
    #         try:
    #             order_line._compute_tax_id()
    #         except ValidationError as e:
    #             # The validation may occur in backend (eg: taxcloud) but should fail silently in frontend
    #             _logger.debug("ValidationError occurs during tax compute. %s" % (e))
    #         if add_qty:
    #             add_qty -= 1
    #
    #     # compute new quantity
    #     if set_qty:
    #         quantity = set_qty
    #     elif add_qty is not None:
    #         quantity = order_line.product_uom_qty + (add_qty or 0)
    #
    #     # ########################################################################
    #     # # Calculate values by including no of users in qty of sale order
    #     #
    #     config_path = self.env['ir.config_parameter'].sudo()
    #     config_user_product = config_path.search(
    #         [('key', '=', 'user_product')]).value
    #     config_product = self.env['product.product'].sudo().search([('id', '=', int(config_user_product))])
    #     plan_users = config_path.search([('key', '=', 'plan_users')]).value
    #
    #     # print('\n\n Order line ',order_line, order_line.order_id, order_line.product_id.id, config_product.id)
    #     config_product_flag = False
    #     if order_line.product_id.id == config_product.id:
    #         config_product_flag = True
    #
    #     # if order_line.order_id.billing == 'normal':
    #     #     if add_qty != None and order_line.order_id.saas_order:
    #     #         if not config_product_flag:
    #     #             if order_line:
    #     #                 # print('llllllllllllllllllllllllllllllllllll', quantity, order_line.order_id.no_of_users)
    #     #                 quantity = quantity * order_line.order_id.no_of_users
    #     #             elif order_line.order_id.no_of_users > 0 :
    #     #                     if product_id != config_product.id and order_line.product_uom_qty == 1:
    #     #                         print('\n\n Order line2 ', order_line.order_id.no_of_users, order_line.product_uom_qty)
    #     #                         quantity = float(order_line.order_id.no_of_users) * order_line.product_uom_qty
    #     # else:
    #     #     if product_id == config_product.id and  add_qty != None:
    #     #         print('asdfsdfsad : ', quantity, order_line.product_uom_qty, '____________', plan_users)
    #     #         if quantity > 0 and not line_id and set_qty:
    #     #             quantity = abs(quantity - float(plan_users))
    #     # print("\n\nquantity : ", quantity)
    #     #######################################################################
    #
    #     # Remove zero of negative lines
    #     if quantity <= 0:
    #         linked_line = order_line.linked_line_id
    #         order_line.unlink()
    #         if linked_line:
    #             # update description of the parent
    #             linked_product = product_with_context.browse(linked_line.product_id.id)
    #             linked_line.name = linked_line.get_sale_order_line_multiline_description_sale(linked_product)
    #     else:
    #         # update line
    #         no_variant_attributes_price_extra = [ptav.price_extra for ptav in order_line.product_no_variant_attribute_value_ids]
    #         values = self.with_context(no_variant_attributes_price_extra=tuple(no_variant_attributes_price_extra))._website_product_id_change(self.id, product_id, qty=quantity)
    #         if self.pricelist_id.discount_policy == 'with_discount' and not self.env.context.get('fixed_price'):
    #             order = self.sudo().browse(self.id)
    #             product_context.update({
    #                 'partner': order.partner_id,
    #                 'quantity': quantity * order_line.order_id.no_of_users if order_line.order_id.saas_order and config_product_flag == False and add_qty == None and order_line.order_id.no_of_users else quantity,
    #                 'date': order.date_order,
    #                 'pricelist': order.pricelist_id.id,
    #             })
    #
    #             product_with_context = self.env['product.product'].with_context(product_context).with_company(order.company_id.id)
    #             product = product_with_context.browse(product_id)
    #
    #             values['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
    #                 order_line._get_display_price(product),
    #                 order_line.product_id.taxes_id,
    #                 order_line.tax_id,
    #                 self.company_id
    #             )
    #
    #         ########################################################################
    #         # Avoid Multiply user count for product manage users
    #         #
    #         if order_line.order_id.billing == 'normal':
    #             if add_qty != None and order_line.order_id.saas_order:
    #                 if order_line.product_id.id != config_product.id:
    #                     if order_line.order_id.no_of_users > 0:
    #                         values['product_uom_qty'] = quantity / order_line.order_id.no_of_users
    #                     print('\n\n\njjjjjjjjjjjjjjjjjjj2', values)
    #         else:
    #             if add_qty != None and order_line.product_id.id == config_product.id:
    #                 values['product_uom_qty'] = quantity  float(plan_users)
    #                 print('\n\n\njjjjjjjjjjjjjjjjjjj4', values)
    #         # ########################################################################
    #
    #         if kwargs.get('extra_users_price') and order_line.product_id.id == config_product.id:
    #             values['price_unit']=kwargs.get('extra_users_price')
    #
    #         order_line.write(values)
    #
    #         # link a product to the sales order
    #         if kwargs.get('linked_line_id'):
    #             linked_line = SaleOrderLineSudo.browse(kwargs['linked_line_id'])
    #             order_line.write({
    #                 'linked_line_id': linked_line.id,
    #             })
    #             linked_product = product_with_context.browse(linked_line.product_id.id)
    #             linked_line.name = linked_line.get_sale_order_line_multiline_description_sale(linked_product)
    #         # Generate the description with everything. This is done after
    #         # creating because the following related fields have to be set:
    #         # - product_no_variant_attribute_value_ids
    #         # - product_custom_attribute_value_ids
    #         # - linked_line_id
    #         order_line.name = order_line.get_sale_order_line_multiline_description_sale(product)
    #
    #     option_lines = self.order_line.filtered(lambda l: l.linked_line_id.id == order_line.id)
    #
    #     return {'line_id': order_line.id, 'quantity': quantity, 'option_ids': list(set(option_lines.ids))}

#
# class SaleOrderLineInherit(models.Model):
#     _inherit = 'sale.order.line'
    # commented 15
    # @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    # def _compute_amount(self):
    #     """
    #     Compute the amounts of the SO line.
    #     """
    #     order_id = self.order_id
    #
    #     config_path = self.env['ir.config_parameter'].sudo()
    #     db_space = config_path.search([('key', '=', 'filestore_size_usage_product')]).value
    #     filestore_space = config_path.search([('key', '=', 'db_size_usage_product')]).value
    #     user_product = config_path.search([('key', '=', 'user_product')]).value
    #     # _logger.info('\n\n{} {} {}\n\n'.format(db_space,filestore_space,user_product))
    #     exclude_product_ids = [int(db_space), int(filestore_space), int(user_product)]
    #     # Update price list amounts of sale orders
    #     # if order_id:
    #     #     # print('PricelistBefore Update : 1 ', order_id.pricelist_id)
    #     #     if order_id.order_line and len(order_id.order_line) == 1:
    #     #         if order_id.order_line.product_id.id not in exclude_product_ids:
    #     #             order_id.update_prices()
    #     #     else:
    #     #         order_id.update_prices()
    #         # print('Pricelistafter Update : 2 ', order_id.pricelist_id)
    #
    #     for line in self:
    #         print('\n\n line.price_unit :', line.order_id, line.price_unit)
    #         order_id = line.order_id
    #
    #         price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
    #         users = line.order_id.no_of_users if order_id.billing == 'normal' else 1
    #         taxes = line.tax_id.compute_all(price, line.order_id.currency_id,
    #                                         line.product_uom_qty,
    #                                         product=line.product_id, partner=line.order_id.partner_shipping_id,
    #                                         users=users)
    #         tax = (taxes['total_included'] - taxes['total_excluded'])
    #
    #         if line.month:
    #             price_subtotal = taxes['total_excluded'] * line.month
    #             if line.month > 0 and line.order_id.no_of_users > 0:
    #                 line.update({
    #                     'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
    #                     'price_total': price_subtotal + tax,
    #                     'price_subtotal': price_subtotal,
    #                 })
    #             else:
    #                 for line in self:
    #                     order = line.order_id
    #                     price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
    #                     users = line.order_id.no_of_users if line.order_id.billing == 'normal' else 1
    #                     taxes = line.tax_id.compute_all(price, line.order_id.currency_id,
    #                                                     line.product_uom_qty,
    #                                                     product=line.product_id,
    #                                                     partner=line.order_id.partner_shipping_id,
    #                                                     users=users)
    #                     tax = (taxes['total_included'] - taxes['total_excluded'])
    #                     price_subtotal = taxes['total_excluded']
    #                     line.update({
    #                         'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
    #                         'price_total': price_subtotal + tax,
    #                         'price_subtotal': price_subtotal,
    #                     })
    #             print("\nline    :",line)

