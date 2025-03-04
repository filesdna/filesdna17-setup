from odoo import models,fields,_,api
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class sale_order(models.Model):
    _inherit = 'sale.order'

    db_space = fields.Boolean('DB space', readonly=True, default=False)
    filestore_space = fields.Boolean('Filestore space', readonly=True, default=False)
    tenant_language = fields.Many2one('res.lang', 'Tenant Language', readonly=False)


    def _website_product_id_change(self, order_id, product_id, qty=0):
        order = self.sudo().browse(order_id)
        product_context = dict(self.env.context)
        product_context.setdefault('lang', order.partner_id.lang)
        product_context.update({
            'partner': order.partner_id,
            'quantity':qty,
            'date': order.date_order,
            'pricelist': order.pricelist_id.id,
        })
        product = self.env['product.product'].with_context(product_context).with_company(order.company_id.id).browse(product_id)
        discount = 0
        if order.pricelist_id.discount_policy == 'without_discount':
            # This part is pretty much a copy-paste of the method '_onchange_discount' of
            # 'sale.order.line'.
            price, rule_id = order.pricelist_id.with_context(product_context).get_product_price_rule(product, qty or 1.0, order.partner_id)
            pu, currency = request.env['sale.order.line'].with_context(product_context)._get_real_price_currency(product, rule_id, qty, product.uom_id, order.pricelist_id.id)
            if pu != 0:
                if order.pricelist_id.currency_id != currency:
                    # we need new_list_price in the same currency as price, which is in the SO's pricelist's currency
                    date = order.date_order or fields.Date.today()
                    pu = currency._convert(pu, order.pricelist_id.currency_id, order.company_id, date)
                discount = (pu - price) / pu * 100
                if discount < 0:
                    # In case the discount is negative, we don't want to show it to the customer,
                    # but we still want to use the price defined on the pricelist
                    discount = 0
                    pu = price
        else:
            pu = product.lst_price
            # if order.no_of_users:
            #     qty = qty / order.no_of_users
            # print('___________________qty ', qty)
            if order.pricelist_id and order.partner_id:
                order_line = order._cart_find_product_line(product.id)
                if order_line:
                    pu = self.env['account.tax']._fix_tax_included_price_company(pu, product.taxes_id, order_line[0].tax_id, self.company_id)

        return {
            'product_id': product_id,
            'product_uom_qty': qty,
            'order_id': order_id,
            'product_uom': product.uom_id.id,
            # 'price_unit': pu,
            'discount': discount,
        }
    # ******************Aj************************
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        """ Add or set product quantity, add_qty can be negative """
        print("_cart udpate >>>>>>>>>>>>\n" * 10)
        self.ensure_one()
        product_context = dict(self.env.context)
        product_context.setdefault('lang', self.sudo().partner_id.lang)
        SaleOrderLineSudo = self.env['sale.order.line'].sudo().with_context(product_context)
        # change lang to get correct name of attributes/values
        product_with_context = self.env['product.product'].with_context(product_context)
        _logger.info('context @@@@@@@@@@@@@@@@@@ {}--- {}---- {}'.format(product_id, product_context, self.env.context))

        product = product_with_context.browse(int(product_id))

        config_path = self.env['ir.config_parameter'].sudo()
        config_user_product = config_path.search(
            [('key', '=', 'user_product')]).value
        config_product = self.env['product.product'].sudo().search([('id', '=', int(config_user_product))])
        plan_users = config_path.search([('key', '=', 'plan_users')]).value

        try:
            if add_qty:
                add_qty = int(add_qty)
        except ValueError:
            add_qty = 1
        try:
            if set_qty:
                set_qty = int(set_qty)
        except ValueError:
            set_qty = 0
        quantity = 0
        order_line = False
        if self.state != 'draft':
            request.session['sale_order_id'] = None
            raise UserError(_('It is forbidden to modify a sales order which is not in draft status.'))
        _logger.info('line_id @@@@@@@@@@@@@@@@@@ {}'.format(line_id))
        if line_id is not False:
            order_line = self._cart_find_product_line(product_id, line_id, **kwargs)[:1]
        lines = False
        
        _logger.info('order_line @@@@@@@@@@@@@@@@@@ {}----------- {}'.format(order_line, product))
        # Create line if no line with product_id can be located
        if not order_line:
            if not product:
                raise UserError(_("The given product does not exist therefore it cannot be added to cart."))

            no_variant_attribute_values = kwargs.get('no_variant_attribute_values') or []
            received_no_variant_values = product.env['product.template.attribute.value'].browse([int(ptav['value']) for ptav in no_variant_attribute_values])
            received_combination = product.product_template_attribute_value_ids | received_no_variant_values
            product_template = product.product_tmpl_id

            # handle all cases where incorrect or incomplete data are received
            combination = product_template._get_closest_possible_combination(received_combination)

            # get or create (if dynamic) the correct variant
            product = product_template._create_product_variant(combination)

            if not product:
                raise UserError(_("The given combination does not exist therefore it cannot be added to cart."))

            product_id = product.id

            values = self._website_product_id_change(self.id, product_id, qty=1)

            # add no_variant attributes that were not received
            for ptav in combination.filtered(lambda ptav: ptav.attribute_id.create_variant == 'no_variant' and ptav not in received_no_variant_values):
                no_variant_attribute_values.append({
                    'value': ptav.id,
                })

            # save no_variant attributes values
            if no_variant_attribute_values:
                values['product_no_variant_attribute_value_ids'] = [
                    (6, 0, [int(attribute['value']) for attribute in no_variant_attribute_values])
                ]

            # add is_custom attribute values that were not received
            custom_values = kwargs.get('product_custom_attribute_values') or []
            received_custom_values = product.env['product.template.attribute.value'].browse([int(ptav['custom_product_template_attribute_value_id']) for ptav in custom_values])

            for ptav in combination.filtered(lambda ptav: ptav.is_custom and ptav not in received_custom_values):
                custom_values.append({
                    'custom_product_template_attribute_value_id': ptav.id,
                    'custom_value': '',
                })

            # save is_custom attributes values
            if custom_values:
                values['product_custom_attribute_value_ids'] = [(0, 0, {
                    'custom_product_template_attribute_value_id': custom_value['custom_product_template_attribute_value_id'],
                    'custom_value': custom_value['custom_value']
                }) for custom_value in custom_values]
            # create the line
            order_line = SaleOrderLineSudo.create(values)
            
            lines = True

            try:
                order_line._compute_tax_id()
            except ValidationError as e:
                # The validation may occur in backend (eg: taxcloud) but should fail silently in frontend
                _logger.debug("ValidationError occurs during tax compute. %s" % (e))
            if add_qty:
                add_qty -= 1
        # compute new quantity
        if order_line.product_id.id == config_product.id and set_qty and line_id is None:
            quantity = set_qty - abs(float(plan_users))
        elif set_qty:
            quantity = set_qty
        elif add_qty is not None:
            quantity = order_line.product_uom_qty + (add_qty or 0)

        months = 1
        if order_line.product_id and order_line.product_id.is_saas and self.invoice_term_id and self.invoice_term_id.name == 'Yearly':
            months = 12

        
        print("self"*10,self.order_line,order_line,order_line.product_id.name,order_line.product_id.is_saas)
        # self.recompute_coupon_lines()

        # Remove zero of negative lines
        if quantity <= 0:
            linked_line = order_line.linked_line_id
            order_line.unlink()
            if linked_line:
                # update description of the parent
                # linked_product = product_with_context.browse(linked_line.product_id.id)
                linked_line.name = linked_line._get_sale_order_line_multiline_description_sale()
        else:
            # update line
            no_variant_attributes_price_extra = [ptav.price_extra for ptav in order_line.product_no_variant_attribute_value_ids]
            values = self.with_context(no_variant_attributes_price_extra=tuple(no_variant_attributes_price_extra))._website_product_id_change(self.id, product_id, qty=quantity)
            order = self.sudo().browse(self.id)
            if self.pricelist_id.discount_policy == 'with_discount' and not self.env.context.get('fixed_price'):
                product_context.update({
                    'partner': order.partner_id,
                    'quantity': quantity * months,
                    'date': order.date_order,
                    'pricelist': order.pricelist_id.id,
                })
            product_with_context = self.env['product.product'].with_context(product_context).with_company(order.company_id.id)
            product = product_with_context.browse(product_id)
            # values['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
            #     order_line._get_display_price(),
            #     order_line.product_id.taxes_id,
            #     order_line.tax_id,
            #     self.company_id
            #     )
            if kwargs.get('extra_users_price') and order_line.product_id.id == config_product.id:
                values['price_unit']=kwargs.get('extra_users_price')
            # total_price = values['price_unit']
            # print("8"*88,values,self.saas_order,self.no_of_users,self.billing, order_line.product_id.is_saas)
            # if order_line.product_id.is_saas:
            #     if self.invoice_term_id.name == 'Yearly':
            #         if self.billing == 'normal':
            #             values['price_unit'] = total_price*12*self.no_of_users
            #         else:
            #             values['price_unit'] = total_price*12
            #     elif self.invoice_term_id.name == 'Monthly':
            #         if self.billing == 'normal':
            #             values['price_unit'] = total_price*self.no_of_users
            #         else:
            #             values['price_unit'] = total_price*12
                    
            # print("9"*88,values)
            order_line.write(values)
            # link a product to the sales order
            if kwargs.get('linked_line_id'):
                linked_line = SaleOrderLineSudo.browse(kwargs['linked_line_id'])
                order_line.write({
                    'linked_line_id': linked_line.id,
                })
                # linked_product = product_with_context.browse(linked_line.product_id.id)
                linked_line.name = linked_line._get_sale_order_line_multiline_description_sale()
            # Generate the description with everything. This is done after
            # creating because the following related fields have to be set:
            # - product_no_variant_attribute_value_ids
            # - product_custom_attribute_value_ids
            # - linked_line_id
            order_line.name = order_line._get_sale_order_line_multiline_description_sale()

        option_lines = self.order_line.filtered(lambda l: l.linked_line_id.id == order_line.id)
        return {'line_id': order_line.id, 'quantity': quantity, 'option_ids': list(set(option_lines.ids))}
    # ******************************************

    #Dont remove the code(Done by Rushi)

    # def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
    #     """ Add or set product quantity, add_qty can be negative """
    #     # print('\n\n\nasdfsalkfdsfsfsdfsdfsd_____________________________', add_qty, set_qty, kwargs, product_id, line_id)
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
    #
    #     # print('\n\n Order line ',order_line, order_line.order_id, order_line.product_id.id, config_product.id)
    #     config_product_flag = False
    #     if order_line.product_id.id == config_product.id:
    #         config_product_flag = True
    #
    #     if add_qty != None and order_line.order_id.saas_order:
    #         if not config_product_flag:
    #             if order_line:
    #                 # print('llllllllllllllllllllllllllllllllllll', quantity, order_line.order_id.no_of_users)
    #                 quantity = quantity * order_line.order_id.no_of_users
    #             elif order_line.order_id.no_of_users > 0 :
    #                     if product_id != config_product.id and order_line.product_uom_qty == 1:
    #                         # print('\n\n Order line2 ', order_line.order_id.no_of_users, order_line.product_uom_qty)
    #                         quantity = float(order_line.order_id.no_of_users) * order_line.product_uom_qty
    #
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
    #         if add_qty != None and order_line.order_id.saas_order:
    #             if order_line.product_id.id != config_product.id:
    #                 if order_line.order_id.no_of_users > 0:
    #                     values['product_uom_qty'] = quantity / order_line.order_id.no_of_users
    #                 # print('\n\n\njjjjjjjjjjjjjjjjjjj', values)
    #
    #         # ########################################################################
    #
    #         if kwargs.get('extra_users_price') and order_line.product_id.id == config_product.id:
    #             values['price_unit']=kwargs.get('extra_users_price')
    #         # print('Updated line Price : ', values)
    #         order_line.write(values)
    #         # print('\n\n\njjjjjjjjjjjjjjjjjjj', order_line.product_uom_qty, order_line.price_unit)
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

    @api.onchange('invoice_term_id')
    def compute_price_list_prices(self):

        # print('__________________Onchange invoice term',self.invoice_term_id.name)
        self.update_prices()

    @api.onchange('instance_topup_list')
    def onchange_compute_price(self):
        _logger.info("@api.onchange('instance_topup_list')")
        if self.instance_topup_list:
            term = self.instance_topup_list.sale_order_ref.invoice_term_id.id
            self.invoice_term_id = term



    def update_prices(self):
        print('__________________Update Prices Method ')
        self.ensure_one()
        lines_to_update = []
        invoicing_term = self.env['recurring.term'].sudo().search([('id', '=', int(self.invoice_term_id.id))])
        month = 1
        for line in self.order_line.filtered(lambda line: not line.display_type):
            # print('__line product info : ',line.product_id.name , line.product_uom_qty, line.product_id)
            if invoicing_term.name == 'Monthly':
                month = 1
            elif invoicing_term.name == 'Yearly':
                month = 12
            product = line.product_id.with_context(
                partner=self.partner_id,
                quantity=line.product_uom_qty * month,
                date=self.date_order,
                pricelist=self.pricelist_id.id,
                uom=line.product_uom.id
            )
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                line._get_display_price(), line.product_id.taxes_id, line.tax_id, line.company_id)
            if self.pricelist_id.discount_policy == 'without_discount' and price_unit:
                discount = max(0, (price_unit - product.lst_price) * 100 / price_unit)
            else:
                discount = 0
            lines_to_update.append((1, line.id, {'price_unit': price_unit, 'discount': discount}))
            # print('__line product info end: ', lines_to_update)
        self.update({'order_line': lines_to_update})
        self.show_update_pricelist = False
        self.message_notify(body=_("Product prices have been recomputed according to pricelist <b>%s<b> ", self.pricelist_id.display_name))


class res_partner(models.Model):
    _inherit = 'res.partner'
    seq_no = fields.Integer()


