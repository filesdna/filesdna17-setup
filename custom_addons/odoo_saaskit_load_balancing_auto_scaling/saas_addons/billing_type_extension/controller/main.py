# import json
from odoo import http
from odoo.http import request
import json
import time
import datetime
import xmlrpc
import logging
from odoo.exceptions import UserError, ValidationError
# from odoo.addons.website_sale.controllers.main import sitemap_shop
from odoo.addons.website_sale.controllers import main
from odoo import _, _lt
try:
    from odoo.addons.website_sale.controllers.main import WebsiteSale
except:
    from addons.website_sale.controllers.main import WebsiteSale
from ... import saas_product

_logger = logging.getLogger(__name__)


class WebsiteSaleInherited(main.WebsiteSale):

    # @http.route()
    # def shop_payment(self, **post):
    #     order = request.website.sale_get_order()
    #     print("order"*888,order)
    #     # carrier_id = post.get('carrier_id')
    #     # keep_carrier = post.get('keep_carrier', False)
    #     # if keep_carrier:
    #     #     keep_carrier = bool(int(keep_carrier))
    #     # if carrier_id:
    #     #     carrier_id = int(carrier_id)
    #     # if order:
    #     #     order._check_carrier_quotation(force_carrier_id=carrier_id, keep_carrier=keep_carrier)
    #     #     if carrier_id:
    #     #         return request.redirect("/shop/payment")

    # return super(WebsiteSaleInherited, self).shop_payment(**post)

    # @http.route([
    #     '/shop',
    #     '/shop/page/<int:page>',
    #     '/shop/category/<model("product.public.category"):category>',
    #     '/shop/category/<model("product.public.category"):category>/page/<int:page>',
    # ], type='http', auth="public", website=True, sitemap=WebsiteSale.sitemap_shop)
    # def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
    #     res = super(WebsiteSaleInherited, self).shop(page=page, category=category, search=search, min_price=min_price, max_price=max_price, ppg=ppg, **post)
    #     print("res"*888,res)
    #     return res

    @http.route(['/shop/order_confirm'], type='http', auth="public", website=True, sitemap=False)
    def payment_confirmation_order(self, **post):
        """ End of checkout process controller. Confirmation is basically seeing
        the status of a sale.order. State at this point :

         - should not have any context / session info: clean them
         - take a sale.order id, because we request a sale.order and are not
           session dependant anymore
        """

        _logger.info('\n\n Inside shop confirmation')
        ICPSudo = request.env['ir.config_parameter'].sudo()
        brand_website = ICPSudo.search([('key', '=', 'brand_website')]).value
        brand_admin = ICPSudo.search([('key', '=', 'admin_login')]).value
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(brand_website))
        brand_pwd = ICPSudo.search([('key', '=', 'admin_pwd')]).value
        dest_model = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(brand_website))
        trial_days = int(ICPSudo.search([('key', '=', 'free_trial_days')]).value or 0)
        # print('\n\nInside shop confirmation')
        # print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%_____________________________________________________________%", request.session)
        sale_order_id = request.session.get('sale_last_order_id')
        _logger.info('\n\n sale_order_id')
        if not sale_order_id:
            sale_order_id = request.session.get('sale_order_id')

        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            transaction = request.env['payment.transaction'].sudo().search([('reference', 'ilike', order.name)],
                                                                           order='id desc', limit=1)
            if transaction and transaction.state == "error":
                return request.render("saas_product.cancel_confirmation", {'order': order})

            if not order.is_top_up:
                _logger.info('\n\n sale_order_id11111111111111..........')
                # if order.is_tenant_created() is False:
                #     _logger.info('\n\n sale_order_id2222222222222222.........')
                if 'show_payment_acquire' in request.session:
                    try:
                            # order.new_instance = True
                        _logger.info('\n\n action_confirm1 calling.........')
                        order.action_confirm1()
                    except Exception as e:
                        _logger.info('Exceiption : {} '.format(e))
                        order.action_confirm1()
            else:
                _logger.info('\n\n action cofirm')

                order.action_confirm1()

            # _logger.info('\n\n Before Action Confirm method session dict: {}'.format(request.session))
            # if 'show_payment_acquire' in request.session:
            #     order.action_confirm1()
            #     _logger.info('\n\n Sale order confirmed successfully')
            #
            # else:
            #     _logger.info('\n\n show_payment_aquirer not found in session dict: {}'.format(request.session))

        else:

            raise UserError('no sale order')
        if 'show_payment_acquire' in request.session:
            del request.session['show_payment_acquire']
        if 'showing' in request.session:
            del request.session['showing']
        if 'select_payment_option' in request.session:
            del request.session['select_payment_option']
        #####################################################################
        # Calculate expiry date with selected term , only when the db is paid
        #####################################################################
        total_days = 0
        if order.invoice_ids.payment_state == 'paid':
            if order.invoice_term_id.name == 'Monthly':
                total_days = 30
            elif order.invoice_term_id.name == 'Yearly':
                total_days = 365
            if total_days:
                date = datetime.datetime.now().date()
                db = request.env['tenant.database.list'].sudo().search([('name', '=', order.instance_name)])
                db.exp_date = date + datetime.timedelta(days=total_days)
        # _logger.info('############################################\n\nUpdating paid db users count after payment')
        ############################################
        # Updating paid db users count after payment
        ############################################
        config_path = request.env['ir.config_parameter'].sudo()
        user_product = config_path.search(
            [('key', '=', 'user_product')]).value
        product = request.env['product.product'].sudo().search([('id', '=', int(user_product))])


        # print("\n\n Product : ", user_product, product, order, order.invoice_ids, order.invoice_ids.line_ids)
        for lines in order.invoice_ids.line_ids:
            # print("\n\nlines : ", lines, order.invoice_ids.payment_state,product)
            if (lines.product_id.name == product.name) and (order.invoice_ids.payment_state == 'paid'):
                db = request.env['tenant.database.list'].sudo().search([('name', '=', order.instance_topup_list.name if order.instance_topup_list.name  else order.instance_name)])
                db_name = db.name

                uid_dst = common.authenticate(db_name, brand_admin, brand_pwd, {})
                # print("\n\n\ndb : ", db, db_name, uid_dst)
                users_count = 0
                name = 'increased'
                if db:
                    agreement_id = request.env['sale.recurring.orders.agreement'].sudo().search(
                        [('partner_id', '=', order.partner_id.id),
                         ('active', '=', True),
                         ('instance_name', '=', db_name)])
                    request.env['sale.recurring.orders.agreement.order'].sudo().create(
                        {
                            'agreement_id': agreement_id[0].id,
                            'order_id': order.id,
                        })
                    # linking invoice to tenant agrements
                    for inv in order.invoice_ids:
                        if not inv.agreement_id:
                            inv.agreement_id = agreement_id.id
                    # end

                    for line in order.order_line:
                        if line.product_id.id == product.id:
                            _logger.info("line.product_id.id == product.id:-------------->")
                            db.no_of_users += line.product_uom_qty
                            users = db.no_of_users
                            users_count += line.product_uom_qty
                            ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'saas.service', 'search', [[]])
                            dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'saas.service', 'write',
                                                  [ids,
                                                   {
                                                       'user_count': users
                                                   }]
                                                  )
                            saas_product.controller.main.saas_pro.send_user_increase_mail(self, db_name, name,
                                                                                          users_count)




                    users = db.no_of_users
                    # print("\n\n\nUsers : ", order.order_line.product_uom_qty,db.no_of_users, users)
                    record = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'saas.service', 'search',
                                                   [[]], {'limit': 1})
                    _logger.info("Record in the Web-->>{}".format(record))
                    dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'saas.service', 'write',
                                          [record, {
                                               'user_count': users
                                           }])
                    saas_product.controller.main.saas_pro.send_user_increase_mail(self,db_name, name, users_count)
                    if agreement_id and agreement_id.agreement_line:
                        exist = False
                        agreement_line_id = False
                        for a_line in agreement_id.agreement_line:
                            if a_line.product_id.id == line.product_id.id:
                                exist = True
                                agreement_line_id = a_line
                                break
                        if exist:
                            agreement_line_id.quantity += line.product_uom_qty
                        else:
                            values_2 = {
                                'agreement_id': agreement_id.id,
                                'product_id': line.product_id.id,
                                'name': line.product_id.name,
                                'quantity': line.product_uom_qty,
                                'price': line.price_unit,
                                'ordering_interval': '1',
                                'ordering_unit': 'years',
                                'createdate': time.strftime('%Y-%m-%d %H:%M:%S'),
                            }

                            request.env['sale.recurring.orders.agreement.line'].sudo().create(
                                values_2)
        ############################################
        # Updating user database size after payment
        ############################################
        config_path = request.env['ir.config_parameter'].sudo()
        brand_website = config_path.search([('key', '=', 'brand_website')]).value
        brand_admin = config_path.search([('key', '=', 'admin_login')]).value
        brand_pwd = config_path.search([('key', '=', 'admin_pwd')]).value
        dest_model = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(brand_website))
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(brand_website))

        prod = 0
        db_size_product = False
        if order.db_space == True:
            prod = 1
            db_size_product = config_path.search(
                [('key', '=', 'db_size_usage_product')]).value
        elif order.filestore_space == True:
            prod = 1
            db_size_product = config_path.search(
                [('key', '=', 'filestore_size_usage_product')]).value
        if prod == 1:
            db = request.env['tenant.database.list'].sudo().search([('name', '=',
                order.instance_topup_list.name if order.instance_topup_list.name else order.instance_name)])
            db_name = db.name
            _logger.info("db_name-->>{}".format(db_name))
            db_product = request.env['product.product'].sudo().search([('id', '=', int(db_size_product))])
            agreement_id = request.env['sale.recurring.orders.agreement'].sudo().search(
                [('partner_id', '=', order.partner_id.id),
                 ('active', '=', True),
                 ('instance_name', '=', db_name)])
            if agreement_id:
                request.env['sale.recurring.orders.agreement.order'].sudo().create(
                    {
                        'agreement_id': agreement_id[0].id,
                        'order_id': order.id,
                    })
            for lines in order.invoice_ids.line_ids:
                if (db_product.name in lines.name) and (order.invoice_ids.payment_state == 'paid'):
                    uid_dst = common.authenticate(db_name, brand_admin, brand_pwd, {})
                    db = request.env['tenant.database.list'].sudo().search([('name', '=', db_name)])
                    record = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'saas.service', 'search',
                                                   [[]], {'limit': 1})
                    if order.db_space == True:
                        prod_qty = 0
                        for line in order.order_line:
                            if line.product_id.id == int(db_size_product):
                                prod_qty = line.product_uom_qty
                                break
                        tot_size = db.tenant_db_size + prod_qty

                        dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'saas.service', 'write',
                                              [record,
                                               {
                                                   'tenant_db_size': tot_size,

                                               }]
                                              )

                        db.tenant_db_size = tot_size
                    elif order.filestore_space == True:
                        prod_qty = 0
                        for line in order.order_line:
                            if line.product_id.id == int(db_size_product):
                                prod_qty = line.product_uom_qty
                                break
                        tot_size = db.tenant_filestore_size + prod_qty
                        dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'saas.service', 'write',
                                              [record,
                                               {
                                                   'tenant_filestore_size': tot_size,

                                               }]
                                              )
                        db.tenant_filestore_size = tot_size
                    # linking invoice to tenant agrements
                    for inv in order.invoice_ids:
                        if not inv.agreement_id:
                            inv.agreement_id = agreement_id.id
                    for line in order.order_line:
                        if agreement_id and agreement_id.agreement_line:
                            exist = False
                            agreement_line_id = False
                            for a_line in agreement_id.agreement_line:
                                if a_line.product_id.id == line.product_id.id:
                                    exist = True
                                    agreement_line_id = a_line
                                    break
                            if exist:
                                agreement_line_id.quantity += line.product_uom_qty
                            else:
                                values_2 = {
                                    'agreement_id': agreement_id.id,
                                    'product_id': line.product_id.id,
                                    'name': line.product_id.name,
                                    'quantity': line.product_uom_qty,
                                    'price': line.price_unit,
                                    'ordering_interval': '1',
                                    'ordering_unit': 'years',
                                    'createdate': time.strftime('%Y-%m-%d %H:%M:%S'),
                                }

                                request.env['sale.recurring.orders.agreement.line'].sudo().create(
                                    values_2)
        return request.render("saas_product.confirmation1", {'order': order})

    @http.route(['/shop/getDefaultBillingType'], type='http', auth="public", website=True)
    def getdefaultbillingtype(self, **post):
        ICPSudo = request.env['ir.config_parameter'].sudo()
        billing = ICPSudo.search([('key', '=', 'billing')]).value
        vals = {'billing_type': billing}
        return json.dumps(vals)


    @http.route(['/shop/getTenantDbCreationProcess'], type='http', auth="public", website=True)
    def get_default_db_creation_method(self, **post):
        manual = request.env['ir.config_parameter'].sudo().get_param('billing_type_extension.manual')
        automated = request.env['ir.config_parameter'].sudo().get_param('billing_type_extension.automated')
        based_on = request.env['ir.config_parameter'].sudo().get_param('billing_type_extension.based_on')
        vals = {'manual': manual,'automated':automated,'based_on':based_on}
        return json.dumps(vals)

# end

    @http.route(['/shop/topup_billing_type'], type='http', auth="public", website=True)
    def topup_billing_type(self, **post):
        instance_rec = request.env['tenant.database.list'].sudo().search([('id','=', int(post.get('instance_id')))], limit=1)
        # ICPSudo = request.env['ir.config_parameter'].sudo()
        # billing = ICPSudo.search([('key', '=', 'billing')]).value
        #
        vals = {'instance_billing_type': instance_rec.billing}
        return json.dumps(vals)

    @http.route(['/shop/get_instance_name'], type='http', auth="public", website=True)
    def get_instance_name(self, **post):
        manual = request.env['ir.config_parameter'].sudo().get_param('billing_type_extension.manual')
        return json.dumps({'db_creation_process':bool(manual)})

    @http.route(['/shop/get_default_plan_users'], type='http', auth="public", website=True)
    def get_default_plan_users(self, **post):
        _logger.info('\n\nget_default_plan_users method.........................')
        plan_users = 1
        if post.get('val') != 'normal':
            ICPSudo = request.env['ir.config_parameter'].sudo()
            plan_users = int(ICPSudo.search([('key', '=', 'plan_users')]).value or 1)

        return json.dumps({'plan_users': plan_users})

    @http.route(['/shop/get_user_product_price'], type='http', auth="public", website=True)
    def getuserProductSalePrice(self):
        ICPSudo = request.env['ir.config_parameter'].sudo()
        product_id = int(ICPSudo.search([('key', '=', 'user_product')]).value)
        ManageUserProduct = request.env['product.product'].search([('id', 'in', [product_id])], limit=1)
        # ManageUserProduct = request.env['product.product'].browse(product_id)
        print(ManageUserProduct.get_list_price(), "_______", product_id, "______________",
              ICPSudo.search([('key', '=', 'user_product')]).value)
        if ManageUserProduct:
            val = {'price': ManageUserProduct.get_list_price()}
        else:
            val = {'price': 0}
        return json.dumps(val)

    @http.route(['/shop/checkout2buy'], type='http', auth="public", website=True)
    def checkout2buy(self, **post):
        ICPSudo = request.env['ir.config_parameter'].sudo()
        trial_days = int(ICPSudo.search([('key', '=', 'free_trial_days')]).value or 0)
        manual = request.env['ir.config_parameter'].sudo().get_param('billing_type_extension.manual')

        # if 'new_instance' in post and post['new_instance'] in [True, 'True', 'true'] and trial_days > 0:
        #     request.session['show_payment_acquire'] = False
        # else:
        #     request.session['show_payment_acquire'] = True

        # order_test = request.website.sale_get_order()

        # sale_order_test = request.env['sale.order'].sudo().search([('id', '=', int(request.session['sale_order_id']))])
        sale_order = False

        # pricelist_id = request.session.get('website_sale_current_pl') or request.env[
        #     'website'].get_current_pricelist().id
        partner = request.env.user.partner_id
        # pricelist = request.env['product.pricelist'].browse(pricelist_id).sudo()
        so_data = request.env['website'].browse(1)._prepare_sale_order_values(partner)
        
        so_data['instance_name'] = post.get('dbname')
        if 'term' in post:
            if not request.session.get('current_billing_frequency'):
                term = request.env['recurring.term'].sudo().search([('type', 'ilike', post.get('term'))], limit=1)
                so_data['invoice_term_id'] = term.id
            else:
                so_data['invoice_term_id'] = request.session.get('current_billing_frequency')
            so_data['no_of_users'] = post.get('num')
            so_data['is_top_up'] = False
            so_data['new_instance'] = True
            so_data['billing'] = post.get('billing_type')
            so_data['tenant_language'] = int(post.get('language'))
            arabic = False
            if post.get('language') == '3':
                arabic = True

        print("\n\nso_data : ", so_data)
        print("\n\nso_data........................................iiiiiiiiiiiiiiiiiiiiiiijjjjjjjjjjjjjjjjjjjjjjjj : ", so_data)
        if 'sale_order_id' in request.session and request.session['sale_order_id']:
            sale_order = request.env['sale.order'].sudo().search([('id', '=', int(request.session['sale_order_id']))])
            sale_order.write(so_data)

        else:
            sale_order = request.env['sale.order'].sudo().create(so_data)
            request.session['sale_order_id'] = sale_order.id
            for order_line in sale_order.order_line:
                order_line.product_uom_qty = post.get('num')

        # Delete/Unlink exist product lines
        exist_ids = []
        for item in sale_order.order_line:
            exist_ids.append((3, item.id, False))
        sale_order.order_line = exist_ids

        if post.get('ids'):
            if 'product_ids' in request.session:
                request.session['product_ids'] = ''

            request.session['product_ids'] = post.get('ids')
            id_list = post.get('ids').split(',')
            id_list = list(map(int, id_list))
            print('\n\nproduct List ids : ', id_list)
            for id in id_list:
                sale_order._cart_update(product_id=id, set_qty=1)

        exist = False
        order = request.env['sale.order'].sudo().search([('state', '=', 'sale'), ('id', '!=', sale_order.id)])
        domain_name = ICPSudo.search([('key', '=', 'domain_name')]).value

        brand_exist = False
        if domain_name:
            record = str(domain_name)
            _logger.info("if testing in local change code to --->>result = record[:record.index(':')]")
            result = record[:record.index(':')]
            if result == post['dbname']:
                brand_exist = True
        for sale in request.env['sale.order'].sudo().search(
                [('state', 'not in', ['draft', 'cancel']), ('id', '!=', sale_order.id)]):
            if sale.instance_name and sale.instance_name == post['dbname']:
                exist = True
                break
        if not exist:
            if sale_order.instance_name:
                if sale_order.is_tenant_created():
                    exist = True
        return json.dumps({'exist': exist,'lang':arabic,'db_creation_process':bool(manual),'brand_exist':brand_exist})

    @http.route('/check/installed_apps', type='json', auth='public', website=True)
    def check_installed_apps(self, **kw):
        """
            Method called by ajax to get installed apps in selected tenants for topup orders
        :param kw: Tanant Database id
        :return: list of installed apps

        """
        tenant_db = request.env['tenant.database.list'].sudo().search([('id', '=', int(kw.get('database_id')))])
        agreement = request.env['sale.recurring.orders.agreement'].sudo().search(
            [('instance_name', '=', tenant_db.name)])
        installed_products = []
        for line in agreement.mapped('agreement_line'):
            ele_id = 'product_{}'.format(line.product_id.id)
            installed_products.append(ele_id)

        return json.dumps({'installed_products': installed_products})

    @http.route('/shop/payment', type='http', auth="public", website=True, sitemap=False)
    def shop_payment(self, **post):
        #     res = super(WebsiteSaleInherited, self).shop_payment(**post)
        #     print("res"*888,res)
        #     return res
        _logger.info('\n\nshop_payment method.........................{}'.format(post))
        order = request.website.sale_get_order()
        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection
        _logger.info('\n\nRedirection skeeped .........................{}'.format(redirection))

        render_values = self._get_shop_payment_values(order, **post)
        db_name = render_values['website_sale_order'].instance_name
        db = request.env['tenant.database.list'].sudo().search([('name', '=', db_name)])
        _logger.info('\n\nRender values 1 : {}'.format(render_values))
        if render_values['errors']:
            render_values.pop('acquirers', '')
            render_values.pop('tokens', '')
        # if 'sale_order_id' in request.session:
        #     request.session['sale_order_id']=''
        show = False
        if 'showing' in request.session:
            if request.session['showing'] == 2:
                render_values['showing'] = 2

        ICPSudo = request.env['ir.config_parameter'].sudo()
        if 'show_payment_acquire' in request.session and request.session['show_payment_acquire'] is True:
            show = True
        _logger.info('\n\nRender values 1 show_payment_acquire : {}'.format(request.session))
        trial_days = int(ICPSudo.search([('key', '=', 'free_trial_days')]).value or 0)
        render_values['show_payment_acquire'] = show
        render_values['free_days'] = trial_days
        _logger.info('\n\nRender values 2 show_payment_acquire : {}'.format(render_values))
        # IF SHOW PAYMENTS DETAILS IS FALSE THE CARRY ONLY ONE ACQUIRER "WIRE TRANSFER"
        if show is False:
            acq = []
            for item in render_values['providers_sudo']:
                if 'Wire' in item.name or item.code == 'custom':
                    acq.append(item)
            render_values['providers_sudo'] = acq

            render_values['hide_acquirer_div'] = True
        else:
            render_values['hide_acquirer_div'] = False

        _logger.info('\n\nRender values 3 show_payment_acquire : {}'.format(render_values))

        if show is True:
            acq = []
            for item in render_values['providers_sudo']:
                payment_mth = ICPSudo.search([('key', '=', 'payment_acquire')]).value
                acquire = request.env['payment.provider'].sudo().search([('id', '=', int(payment_mth))])
                if acquire.id == item.id:
                    pass
                else:
                    acq.append(item)

        render_values['providers_sudo'] = acq
        _logger.info('\n\nRender values 4 show_payment_acquire : {}'.format(render_values))

        if not (db and db.free_trial == False):
            render_values['trial'] = 'True'
        config_path = request.env['ir.config_parameter'].sudo()
        sale_order_line = render_values['website_sale_order'].mapped("website_order_line")
        user_product = config_path.search(
            [('key', '=', 'user_product')]).value
        product = request.env['product.product'].sudo().search([('id', '=', int(user_product))])
        if render_values['website_sale_order'].billing == 'normal':  # newly added
            for line in sale_order_line:
                if product == line.product_id:
                    render_values['add_more_user'] = 'True'
        render_values['is_top_up'] = order.is_top_up
        _logger.info('\n\nRender values 5 last  : {}'.format(render_values))
        return request.render("website_sale.payment", render_values)

    @http.route(['/shop/shop_cart_custom_update'], type='http', auth="public", website=True)
    def shop_cart_custom_update(self, **post):
        domain = ''
        _logger.info('==============Inside Shop cart custom update {} {}'.format(request.session, post))
        try:
            domain = request.httprequest.environ['HTTP_X_FORWARDED_SERVER']
        except:
            domain = request.httprequest.environ['HTTP_HOST']

        path = request.httprequest.environ['PATH_INFO']

        try:
            http = request.httprequest.environ['HTTP_REFERER']
        except:
            http = request.httprequest.environ['HTTP_X_FORWARDED_PROTO']

        if 'https' in http:
            http = 'https://'
        else:
            http = 'http://'

        if not request.session.uid:
            url = "/web/login?redirect=" + str(http) + "/" + str(domain) + "/" + str(path)
            url = url.replace('//', '/')
            return request.redirect(url)
        order = False

        order = request.website.sale_get_order()
        _logger.info('\n\nSession Products : {}'.format(request.session))
        if order:
            _logger.info('\n\nWebsite Order Line : {} ->>>>>> {}'.format(order, order.website_order_line))
            for line in order.website_order_line:
                line.unlink()

        print('Before create order session : ', request.session)
        if 'product_ids' in request.session:
            ids = request.session['product_ids']

            ids = ids.split(",")
            pro_ids = []
            pro_ids = list(map(int, ids))
            for item in pro_ids:
                order = request.website.sale_get_order(force_create=1)._cart_update(
                    product_id=int(item),
                )

            ###########################################################################################
            _logger.info('order  : {} '.format(order))

            order = request.website.sale_get_order()
            # print("order :_____________", request.website.sale_get_order(), order.billing)
            if order.billing == 'user_plan_price':
                if not order.is_top_up:
                    config_path = request.env['ir.config_parameter'].sudo()
                    config_user_product = config_path.search(
                        [('key', '=', 'user_product')]).value
                    config_product = request.env['product.product'].sudo().search(
                        [('id', '=', int(config_user_product))])
                    if config_product:
                        order._cart_update(product_id=config_product.id, set_qty=order.no_of_users)
                        print('Updated Cart')
                    else:
                        raise ValidationError('Manager user product not defined yet, Please contact to administrator')

            # print('PricelistBefore Update : 1 ', order.pricelist_id)
            order.update_prices()
            ###########################################################################################
        return request.redirect("/shop/cart")

    def _get_checkout_steps(self, current_step=None):
        """ Return an ordered list of steps according to the current template rendered.

        If current_step is provided, returns only the corresponding step.

        Note: self.ensure_one()

        :param str current_step: The xmlid of the current step, defaults to None.
        :rtype: list
        :return: A list with the following structure:
            [
                [xmlid],
                {
                    'name': str,
                    'current_href': str,
                    'main_button': str,
                    'main_button_href': str,
                    'back_button': str,
                    'back_button_href': str
                }
            ]
        """
        self.ensure_one()
        is_extra_step_active = self.viewref('website_sale.extra_info').active
        redirect_to_sign_in = self.account_on_checkout == 'mandatory' and self.is_public_user()

        partner_id = self.env.user.partner_id

        steps = [(['website_sale.cart'], {
            'name': _lt("Review Order"),
            'current_href': '/shop/cart',
            'main_button': _lt("Sign In") if redirect_to_sign_in else _lt("Checkout"),
            'main_button_href': f'{"/web/login?redirect=" if redirect_to_sign_in else ""}/shop/address?partner_id=%s' % partner_id.id,
            'back_button': _lt("Continue shopping"),
            'back_button_href': '/shop',
        }), (['website_sale.checkout', 'website_sale.address'], {
            'name': _lt("Shipping"),
            'current_href': '/shop/checkout',
            'main_button': _lt("Confirm"),
            'main_button_href': f'{"/shop/extra_info" if is_extra_step_active else "/shop/confirm_order"}',
            'back_button': _lt("Back to cart"),
            'back_button_href': '/shop/cart',
        })]
        if is_extra_step_active:
            steps.append((['website_sale.extra_info'], {
                'name': _lt("Extra Info"),
                'current_href': '/shop/extra_info',
                'main_button': _lt("Continue checkout"),
                'main_button_href': '/shop/confirm_order',
                'back_button': _lt("Return to shipping"),
                'back_button_href': '/shop/checkout',
            }))
        steps.append((['website_sale.payment'], {
            'name': _lt("Payment"),
            'current_href': '/shop/payment',
            'back_button': _lt("Back to cart"),
            'back_button_href': '/shop/cart',
        }))


        if current_step:
            return next(step for step in steps if current_step in step[0])[1]
        else:
            return steps
