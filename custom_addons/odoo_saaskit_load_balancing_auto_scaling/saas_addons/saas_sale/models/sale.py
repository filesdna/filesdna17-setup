# -*- coding: utf-8 -*-
from odoo import fields
import datetime
import odoo
from odoo.api import Environment
from odoo import _, SUPERUSER_ID
import datetime
import logging

_logger = logging.getLogger(__name__)
import time
from functools import partial
from odoo.tools.misc import formatLang
from odoo.tools import config
import logging
import time
from odoo.service import db
from odoo.tools.float_utils import float_round as round
from odoo import api, models
import xmlrpc
from odoo.exceptions import UserError, ValidationError
import traceback
from odoo.http import request
from odoo.addons.website_sale.models.website import Website
import psycopg2
from contextlib import closing
import json
import re

_logger = logging.getLogger(__name__)

ADMINUSER_ID = 2


def sale_get_order(self, force_create=False, code=None, update_pricelist=False, force_pricelist=False,
                   billing_frequency=False):
    _logger.info("sale_get_order---------------------->>>>>>>>>>>>>>>>>>>>>>>>>>>")
    """ Return the current sales order after mofications specified by params.
    :param bool force_create: Create sales order if not already existing
    :param str code: Code to force a pricelist (promo code)
                     If empty, it's a special case to reset the pricelist with the first available else the default.
    :param bool update_pricelist: Force to recompute all the lines from sales order to adapt the price with the current pricelist.
    :param int force_pricelist: pricelist_id - if set,  we change the pricelist with this one
    :returns: browse record for the current sales order
    """
    if not self.env.user:
        return False
    # _logger.info(
    #     '\n\n\nCreate Website Sale order : {} {} {} {}'.format(force_create, code, update_pricelist, force_pricelist))

    self.ensure_one()
    partner = self.env.user.partner_id
    sale_order_id = request.session.get('sale_order_id')
    print("===========sale_order_id==============", sale_order_id)
    if not sale_order_id and not self.env.user._is_public():
        last_order = partner.last_website_so_id
        if last_order:
            available_pricelists = self.get_pricelist_available()
            # Do not reload the cart of this user last visit if the cart uses a pricelist no longer available.
            sale_order_id = last_order.pricelist_id in available_pricelists and last_order.id

    # Test validity of the sale_order_id
    sale_order = self.env['sale.order'].sudo().browse(sale_order_id).exists() if sale_order_id else None
    # print("==========================fvdsfdsds==",sale_order.state)
    if not (sale_order or force_create or code):
        if request.session.get('sale_order_id'):
            request.session['sale_order_id'] = None
        return self.env['sale.order']

    if self.env['product.pricelist'].browse(force_pricelist).exists():
        pricelist_id = force_pricelist
        request.session['website_sale_current_pl'] = pricelist_id
        update_pricelist = True
    else:
        pricelist_id = request.session.get('website_sale_current_pl') or self._get_current_pricelist().id

    if not self._context.get('pricelist'):
        self = self.with_context(pricelist=pricelist_id)

    # cart creation was requested (either explicitly or to configure a promo code)
    if not sale_order:
        # TODO cache partner_id session
        # pricelist = self.env['product.pricelist'].browse(pricelist_id).sudo()
        so_data = self._prepare_sale_order_values(partner)
        print("====d=d=fdf=f=d=f==f=fdf=df")
        sale_order = self.env['sale.order'].with_context(with_company=request.website.company_id.id).sudo().create(
            so_data)

        # set fiscal position
        if request.website.partner_id.id != partner.id:
            sale_order._compute_fiscal_position_id()
        else:  # For public user, fiscal position based on geolocation
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                country_id = request.env['res.country'].search([('code', '=', country_code)], limit=1).id
                fp_id = request.env['account.fiscal.position'].sudo().with_context(
                    force_company=request.website.company_id.id)._get_fpos_by_region(country_id)
                sale_order.fiscal_position_id = fp_id
            else:
                # if no geolocation, use the public user fp
                sale_order._compute_fiscal_position_id()
        print("============================", sale_order.state)
        request.session['sale_order_id'] = sale_order.id

    # case when user emptied the cart
    if not request.session.get('sale_order_id'):
        request.session['sale_order_id'] = sale_order.id

    # check for change of pricelist with a coupon
    pricelist_id = pricelist_id or partner.property_product_pricelist.id
    print("==========pricelist_id===========", pricelist_id)

    # check for change of partner_id ie after signup
    if sale_order.partner_id.id != partner.id and request.website.partner_id.id != partner.id:
        print("djfhdskjfhjdkshfkjhfsd")
        flag_pricelist = False
        if pricelist_id != sale_order.pricelist_id.id:
            flag_pricelist = True
        fiscal_position = sale_order.fiscal_position_id.id

        # change the partner, and trigger the onchange
        sale_order.write({'partner_id': partner.id})
        # sale_order.onchange_partner_id()
        sale_order.write({'partner_invoice_id': partner.id})
        sale_order._compute_fiscal_position_id()  # fiscal position
        sale_order['payment_term_id'] = self.sale_get_payment_term(partner)

        # check the pricelist : update it if the pricelist is not the 'forced' one
        values = {}
        if sale_order.pricelist_id:
            if sale_order.pricelist_id.id != pricelist_id:
                values['pricelist_id'] = pricelist_id
                update_pricelist = True

        # if fiscal position, update the order lines taxes
        if sale_order.fiscal_position_id:
            sale_order.order_line._compute_tax_id()

        # if values, then make the SO update
        if values:
            sale_order.write(values)

        # check if the fiscal position has changed with the partner_id update
        recent_fiscal_position = sale_order.fiscal_position_id.id
        if flag_pricelist or recent_fiscal_position != fiscal_position:
            update_pricelist = True

    if code and code != sale_order.pricelist_id.code:
        code_pricelist = self.env['product.pricelist'].sudo().search([('code', '=', code)], limit=1)
        print("==========code_pricelist======================", code_pricelist)
        if code_pricelist:
            pricelist_id = code_pricelist.id
            print("==========pricelist_id==========", pricelist_id)
            update_pricelist = True
    elif code is not None and sale_order.pricelist_id.code and code != sale_order.pricelist_id.code:
        # code is not None when user removes code and click on "Apply"
        pricelist_id = partner.property_product_pricelist.id
        print("=========pricelist_id==================", pricelist_id)
        update_pricelist = True

    # update the pricelist
    if update_pricelist:
        request.session['website_sale_current_pl'] = pricelist_id
        values = {'pricelist_id': pricelist_id}
        # print("\n\nvalues : ", values)
        sale_order.write(values)
        for line in sale_order.order_line:
            # print('\n\n Line order : ', line.product_uom_qty, sale_order.no_of_users)
            if line.exists():
                sale_order._cart_update(product_id=line.product_id.id, line_id=line.id,
                                        extra_users_price=line.price_unit, add_qty=0)
    print("=============djkfnskdsjkdhdskdhdskhdkshdksahdshds", sale_order)
    return sale_order


Website.sale_get_order = sale_get_order
print("========Website.sale_get_order==============", Website.sale_get_order)


class RPCProxyOne(object):
    def __init__(self, server, ressource):
        """Class to store one RPC proxy server."""
        self.server = server
        local_url = 'http://%s:%d/xmlrpc/common' % (server.server_url,
                                                    server.server_port)
        rpc = xmlrpc.client.ServerProxy(local_url)
        self.uid = rpc.login(server.server_db, server.login, server.password)
        local_url = 'http://%s:%d/xmlrpc/object' % (server.server_url,
                                                    server.server_port)
        self.rpc = xmlrpc.client.ServerProxy(local_url)
        self.ressource = ressource

    def __getattr__(self, name):
        return lambda *args, **kwargs: self.rpc.execute(self.server.server_db,
                                                        self.uid,
                                                        self.server.password,
                                                        self.ressource, name,
                                                        *args)


class RPCProxy(object):
    """Class to store RPC proxy server."""

    def __init__(self, server):
        self.server = server

    def get(self, ressource):
        return RPCProxyOne(self.server, ressource)


class Users(models.Model):
    _inherit = 'res.users'

    tenant_user = fields.Boolean('Tenant User dummy field (no use in master db)')


class sale_order(models.Model):
    _inherit = 'sale.order'

    billing = fields.Selection([('normal', 'Per Module/Per Month/Per User'),
                                ('user_plan_price', 'Users + Plan Price')
                                ], string="Billing Type")

    # @api.depends('order_line.price_total')
    # def _amount_all(self):
    #     """
    #     Compute the total amounts of the SO.
    #     """
    #     for order in self:
    #         amount_untaxed = amount_tax = 0.0
    #         for line in order.order_line:
    #             amount_untaxed += line.price_subtotal
    #             if line.month > 0:
    #                 amount_tax += line.price_tax * line.month
    #             else:
    #                 amount_tax += line.price_tax
    #
    #         order.update({
    #             'amount_untaxed': amount_untaxed,
    #             'amount_tax': amount_tax,
    #             'amount_total': amount_untaxed + amount_tax,
    #         })

    # def _amount_all_temp(self, field_name, arg):
    # """Method overridden as it is without calling 'super' to calculate tax according to no. of months in subscription.
    # """
    # cur_obj = self.env['res.currency']
    # res = {}
    # for order in self:
    #     res[order.id] = {
    #         'amount_untaxed': 0.0,
    #         'amount_tax': 0.0,
    #         'amount_total': 0.0,
    #     }
    #
    #     val = val1 = 0.0
    #     cur = order.pricelist_id.currency_id
    #     for line in order.order_line:
    #         val1 += line.price_subtotal
    #         val += self._amount_line_tax(line)
    #         # multiply by no. of months in a subscription
    #         val *= line.month
    #     res[order.id]['amount_tax'] = cur_obj.round(cur, val)
    #     res[order.id]['amount_untaxed'] = cur_obj.round(cur, val1)
    #     res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
    # return res

    def action_confirm(self):
        print("============action_confirm==inside my module===========", self.state)
        """ Confirm the given quotation(s) and set their confirmation date.
        If the corresponding setting is enabled, also locks the Sale Order.
        :return: True
        :rtype: bool
        :raise: UserError if trying to confirm cancelled SO's
        """
        # self.state = 'draft'
        if not all(order._can_be_confirmed() for order in self):
            raise UserError(_(
                "The following orders are not in a state requiring confirmation: %s",
                ", ".join(self.mapped('display_name')),
            ))
        self.order_line._validate_analytic_distribution()
        for order in self:
            order.validate_taxes_on_sales_order()
            if order.partner_id in order.message_partner_ids:
                continue
            order.message_subscribe([order.partner_id.id])
        self.write(self._prepare_confirmation_values())
        # Context key 'default_name' is sometimes propagated up to here.
        # We don't need it and it creates issues in the creation of linked records.
        context = self._context.copy()
        context.pop('default_name', None)
        self.with_context(context)._action_confirm()
        if self.env.user.has_group('sale.group_auto_done_setting'):
            self.action_lock()
        return True

    def _can_be_confirmed(self):
        self.ensure_one()
        return self.state in {'draft', 'sent'}

    def _find_mail_template(self, force_confirmation_template=False):
        template_id = False

        if force_confirmation_template or (self.state == 'sale' and not self.env.context.get('proforma', False)):
            template_id = int(self.env['ir.config_parameter'].sudo().get_param('sale.default_confirmation_template'))
            template_id = self.env['mail.template'].search([('id', '=', template_id)]).id
            if not template_id:
                template_id = self.env['ir.model.data']._xmlid_to_res_id(
                    'saas_sale.mail_template_sale_confirmation_inherit', raise_if_not_found=False)
        if not template_id:
            template_id = self.env['ir.model.data']._xmlid_to_res_id('sale.email_template_edi_sale',
                                                                     raise_if_not_found=False)

        return template_id

    def check_so_to_confirm(self):
        ## Cron/Scheduler method to check SO's for auto confirm if " Auto process free trial SO's " is checked
        ## This method will search for all SO's having state 'sent' i.e. paid from customer and are not top-up

        sent_sale_orders = self.search(
            [('state', 'in', ['sent', 'draft']), ('is_top_up', '!=', True), ('instance_name', '!=', False)])
        print("------sent_sale_orders-------", sent_sale_orders)
        ## instance_name != False means sale order is a SaaS sale order bcoz normal sale order dosn't have instance name.
        for sent_sale_order in sent_sale_orders:
            #                 self.env['sale.order'].action_confirm(  [sent_sale_order] )
            sent_sale_order.action_confirm()

        return True

    def _get_real_points_for_coupon(self, coupon, post_confirm=False):

        """
        This function is  overideded to solve the issue while giving discount from the website.
        """
        self.ensure_one()
        points = coupon.points
        if coupon.program_id.applies_on != 'future':
            # Points that will be given by the order upon confirming the order
            points += self.coupon_point_ids.filtered(lambda p: p.coupon_id == coupon).points
        # Points already used by rewards
        points -= sum(self.order_line.filtered(lambda l: l.coupon_id == coupon).mapped('points_cost'))
        points = coupon.currency_id.round(points)
        return points

    def update_cart_price(self, post):
        # =======================================================================
        # Method to update product price according to date on which it is purchase
        # If purchase order is at middle of the month don't take cost for all month
        # =======================================================================
        if self.is_top_up:
            ICPSudo = self.env['ir.config_parameter'].sudo()

            for line in self.order_line:
                product = line.product_id
                original_price = 0
                if product.is_saas:
                    price_unit = product.list_price
                    original_price = price_unit
                    instance_name = self.instance_name
                    db_ids = self.env['tenant.database.list'].search([('name', '=', instance_name)], limit=1)
                    exp_date = False
                    if db_ids:
                        exp_date = db_ids.exp_date

                    if exp_date:
                        ##for different subscription terms take respective No .of months
                        months_to_add = 0
                        term_type = db_ids.invoice_term_id.type
                        if term_type == 'from_first_date': months_to_add = 1
                        if term_type == 'quarter': months_to_add = 3
                        if term_type == 'half_year': months_to_add = 6
                        if term_type == 'year': months_to_add = 12

                        ## Find start date from exp_date and no of months, to calculate total days in subscription term
                        start_date = str(datetime.datetime.strptime(str(exp_date), '%Y-%m-%d') - datetime.timedelta(
                            months_to_add * 365 / 12).isoformat())[:10]
                        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")

                        exp_date = datetime.datetime.strptime(exp_date, "%Y-%m-%d")
                        total_days = exp_date - start_date
                        total_days = total_days.total_seconds() / 60 / 60 / 24

                        ##If it is trial period take only trial days configured in configurations.
                        if ICPSudo.search([('key', '=', 'free_trial')]).value:
                            total_days = ICPSudo.search([('key', '=', 'free_trial_days')]).value or 30

                        ##Find remaining days.
                        today_date = datetime.datetime.today()
                        days_to_pay = exp_date - today_date
                        days_to_pay = days_to_pay.total_seconds() / 60 / 60 / 24
                        days_to_pay = days_to_pay + 1  # It was given one day less thats why added 1 day.

                        price_unit_per_day = price_unit / int(total_days)
                        price_unit = price_unit_per_day * int(days_to_pay)
                        if price_unit < 0: price_unit = price_unit * (-1)
                        print('asdfsdfsfsfsdf++++++++++++++++++++++++++++++++++++++++++++++++')
                        line.write({'price_unit': price_unit})
                        self._cr.commit()

                        ##If it is trial period take price as it is.
                        if self.env['tenant.database.list'].browse(db_ids[0]).free_trial:
                            line.write({'price_unit': original_price})

                        self._cr.commit()
        return True

    # @api.model
    # def create(self, vals):
    #     print("\n\n\n\n\n\n\n\n\n@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n\n\n\n\n\n\n\n")
    #     print("vals :________________- ", vals)
    #     if 'is_manage_users' in vals and 'filestore_space' in vals:
    #         if vals['is_manage_users'] and vals['filestore_space']:
    #             _logger.info("inside this error.")
    #             raise ValidationError("Can only select one topup for one sale order!!!")
    #     if 'is_manage_users' in vals and 'db_space' in vals:
    #         if vals['is_manage_users'] and vals['db_space']:
    #             _logger.info("inside this error.")
    #             raise ValidationError("Can only select one topup for one sale order!!!")
    #     if 'db_space' in vals and 'filestore_space' in vals:
    #         if vals['filestore_space'] and vals['db_space']:
    #             _logger.info("inside this error.")
    #             raise ValidationError("Can only select one topup for one sale order!!!")
    #     res = super(sale_order, self).create(vals)
    #     return res

    def write(self, vals=None):
        # print('\n\n\nInside Write function for sale order\n\n\n',vals);

        ##Overridden for auto confirm of Top-Up Order
        if 'no_of_users' in vals:
            print(222, vals)
        res = False
        # self.update_prices()
        if 'confirmation_date' in vals and 'state' in vals and vals['state'] == 'sale':
            self._cr.execute("update sale_order set state='%s' where id =%s" % (vals['state'], self.id))
            self._cr.execute(
                "update sale_order set confirmation_date='%s' where id =%s" % (vals['confirmation_date'], self.id))
            del vals['confirmation_date']
            res = True
            # res = super(sale_order, self).write(vals)
        else:
            try:

                res = super(sale_order, self).write(vals)

            except Exception as e:
                print(e)
        return res

    def copy(self, default=None):
        default = default or {}
        if 'name' in default and default['name'] in ['New, new']:
            default['name'] = self.env['ir.sequence'].next_by_code('sale.order') or _('New')
        if 'name' not in default:
            default['name'] = self.env['ir.sequence'].next_by_code('sale.order') or _('New')

        return super(sale_order, self).copy(default)

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        for vals in vals_list:
            if 'name' in vals and vals['name'] in ['New, new']:
                vals['name'] = self.env['ir.sequence'].next_by_code('sale.order') or _('New')
            if 'name' not in vals:
                vals['name'] = self.env['ir.sequence'].next_by_code('sale.order') or _('New')
            if 'uid' in self._context:
                vals['user_uid'] = self._context['uid']
            if 'is_manage_users' in vals and 'filestore_space' in vals:
                if vals['is_manage_users'] and vals['filestore_space']:
                    _logger.info("inside this error.")
                    raise ValidationError("Can only select one topup for one sale order!!!")
            if 'is_manage_users' in vals and 'db_space' in vals:
                if vals['is_manage_users'] and vals['db_space']:
                    _logger.info("inside this error.")
                    raise ValidationError("Can only select one topup for one sale order!!!")
            if 'db_space' in vals and 'filestore_space' in vals:
                if vals['filestore_space'] and vals['db_space']:
                    _logger.info("inside this error.")
                    raise ValidationError("Can only select one topup for one sale order!!!")
        return models.Model.create(self, vals_list)

    @api.model
    def _is_saas_order(self):
        # =======================================================================
        # Method returns order type, whether it is SaaS type or not
        # =======================================================================
        for sale in self:
            is_saas = False
            if sale.order_line:
                for line in sale.order_line:
                    if line.product_id.is_saas:
                        is_saas = True
                        break
            sale.saas_order = is_saas

    @api.model
    def _get_user_dbs(self):
        # =======================================================================
        # Method to get list of all DB's associated to specific user
        # =======================================================================
        res = {}
        for sale in self:
            db_ids = self.env['tenant.database.list'].search([('user_id', '=', self._context.get('uid'))])
            res[sale.id] = db_ids
        return res

    user_uid = fields.Many2one('res.users', "User")
    instance_name = fields.Char('Database Name', size=64)
    instance_name_list = fields.Many2one('tenant.database.list', compute='_get_user_dbs', string='saaS order')
    saas_order = fields.Boolean(compute='_is_saas_order', string='SaaS Order')
    no_of_users = fields.Integer('No. of Users', default=1)
    # for payment methode(pay now/trial)
    free_trial = fields.Boolean('Free Trial')
    is_top_up = fields.Boolean('Is top-up?')
    new_instance = fields.Boolean('New Instance', readonly=True)
    existed_product = fields.Char('product Name', size=500)
    pwd = fields.Text('Random Generated Password')
    saas_domain = fields.Char('SaaS Domain', size=50, compute="get_tenant_url")
    temp_vals = fields.Char('saaS domain', size=200)
    invoice_term_id = fields.Many2one('recurring.term', 'Invoicing Term')
    company_name = fields.Char('Customer Company Name', size=128)
    customer_name = fields.Char('Customer Name', size=128)
    customer_email = fields.Char('Customer Email Address', size=128)
    lang_code = fields.Char('Language Code', size=64, default='en_US')
    is_manage_users = fields.Boolean('Is Manage Users', readonly=True)
    instance_topup_list = fields.Many2one('tenant.database.list', string='Database Name')

    def get_tenant_url(self):
        so_line = self.env['sale.order'].search([])
        ICPSudo = self.env['ir.config_parameter'].sudo()
        domain = ICPSudo.search([('key', '=', 'domain_name')]).value
        if not domain.startswith('.'):
            domain = '.' + domain
        self.saas_domain = "%s%s" % (self.instance_name, domain)

    def random_password(self):
        # =======================================================================
        # Returns random string containing alphanumeric Characters
        # =======================================================================
        import random
        alphabet = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        pw_length = 8
        mypw = ""
        for i in range(pw_length):
            next_index = random.randrange(len(alphabet))
            mypw = mypw + alphabet[next_index]
        return mypw

    def set_logo(self):
        db_name = str(self.instance_name).lower().replace(" ", "_")
        registry = odoo.registry(db_name)

        ## Set Service provider Company Logo to tenant database initially

        with closing(registry.cursor()) as cr:
            env = Environment(cr, ADMINUSER_ID, {})
            admin_company_ids = self.env['res.company'].search([], limit=1)
            if admin_company_ids:
                tenant_company_ids = env['res.company'].search([])
                for tenant_company in tenant_company_ids:
                    #                     comp_obj=env['res.company'].browse(tenant_company)
                    tenant_company.write({'logo': admin_company_ids.logo})
            cr.commit()

    def _make_invoice(self, order, lines=None):
        invoice_line_obj = self.env['account.move.line']
        if lines and order.saas_order:
            # ===================================================================
            # If product is SaaS type and free trial period give 100% discount
            # ===================================================================
            db_name = order.instance_name
            db_ids = self.env['tenant.database.list'].search([('name', '=', db_name)])
            free_trial = False
            if db_ids:
                free_trial = db_ids.free_trial
            for line in invoice_line_obj.browse(lines):
                if line.product_id.is_saas and free_trial:
                    line.write({'discount': 100})
        _logger.info(_('Inside make invoice function  : {} {}'.format(order, lines)))
        res = super(sale_order, self)._make_invoice(order, lines)
        return res

    def action_install_module(self, db_name, module_list):
        ## XMLRPC CONNECTION
        ICPSudo = self.env['ir.config_parameter'].sudo()
        brand_website = ICPSudo.search([('key', '=', 'brand_website')]).value
        brand_admin = ICPSudo.search([('key', '=', 'admin_login')]).value
        brand_pwd = ICPSudo.search([('key', '=', 'admin_pwd')]).value
        dest_model = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(brand_website))
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(brand_website))
        domain_website = ICPSudo.search([('key', '=', 'domain_name')]).value
        # print("\n\n_____________values to connect ", db_name, brand_admin, brand_pwd)
        uid = 0
        uid_dst = 0
        try:
            uid_dst = common.authenticate(db_name, brand_admin, brand_pwd, {})
            if not uid_dst:
                uid_dst = common.authenticate(db_name, 'admin', 'admin', {})
                brand_pwd = 'admin'
        except Exception as e:
            print('\n\nError ___________ : ', e)

        ## XMLRPC
        max_group_id = max(dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.groups', 'search', [[]]))
        module_ids_to_install = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.module.module', 'search',
                                                      [[('name', 'in', module_list)]])
        try:
            num = 0
            for module_id in module_ids_to_install:
                num = num + 1
                dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.module.module', 'button_immediate_install',
                                      [module_id])
        except Exception as e:
            print(e)
        try:
            dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'perform_many2many_table_work', [2],
                                  {'max_group_id': max_group_id or 9000})
        except Exception as e:
            if 'has no attribute' in str(e):
                pass
            else:
                raise UserError(e)

    def _auto_open_invoice(self, move_id):
        self.env['account.move'].signal_workflow([move_id], 'invoice_open')
        _logger.info('SaaS-post Trail Period invoice is open automatically for invoice %s' % (str(move_id)))
        return True

    @api.onchange('partner_id')
    def _onchange_partner_id_saas(self):
        partner_id = self.partner_id
        # sale_order = self.env['sale.order'].search([('parter_id','=',partner_id.id),('saas_order')])
        tenant_database_list = self.env['tenant.database.list'].search(
            [('sale_order_ref.partner_id', '=', partner_id.id)])
        _logger.info("tenant database list>>>>>>>>>{}".format(tenant_database_list))
        return {'domain': {'instance_topup_list': [('id', 'in', tenant_database_list.ids)]}}

    def _auto_paid_invoice(self, move_id=None):
        _logger.info("\n_auto_paid_invoice----------------------->>\n ")
        ## create account voucher record to create payment
        voucher_obj = self.env['account.move']
        invoice_obj = self.env['account.move']
        journal_obj = self.env['account.journal']
        voucher_line_obj = self.env['account.move.line']
        inv = invoice_obj.browse(move_id)
        '''
            their may be multiple cash type journals has been found, 
            we are consider 1st one to do the payment.    
        '''
        journal_ids = journal_obj.search([('type', '=', 'cash')])
        journal = journal_obj.browse(journal_ids[0])
        if not journal_ids:
            raise UserError(
                _('Warning', 'Did not found any cash type Journal.. Please configure it from Journal Master'))
        partner_id = self.env['res.partner']._find_accounting_partner(inv.partner_id)
        vals = {
            'partner_id': partner_id.id,
            'period_id': inv.period_id.id,
            'amount': inv.type in ('out_refund', 'in_refund') and -inv.residual or inv.residual,
            'reference': inv.name,
            'close_after_process': True,
            'invoice_type': inv.type,
            'move_id': inv.id,
            'type': inv.type in ('out_invoice', 'out_refund') and 'receipt' or 'payment',
            'journal_id': journal_ids[0],
            'account_id': journal.default_credit_account_id.id,
            'date': time.strftime('%Y-%m-%d'),
            'currency_id': inv.currency_id,
            'name': inv.name,
            'number': inv.number,
        }

        voucher_id = voucher_obj.create(vals)
        for move in inv.move_id.line_id:
            line = voucher_line_obj.create({
                'voucher_id': voucher_id,
                'amount': inv.amount_total,
                'amount_original': inv.amount_total,
                'account_id': inv.partner_id.property_account_receivable.id,
                'move_line_id': move.id,
                'type': 'cr',
            })
            break
        conText = self._context
        if conText is None:
            conText = {
                'move_id': inv.id
            }
        voucher_obj.button_proforma_voucher([voucher_id])
        return True

    def top_up_backend_order(self):
        print("=======================")
        tenant_customer = self.instance_topup_list.sale_order_ref.partner_id
        print("==========tenant_customer============", tenant_customer)
        if self.partner_id != tenant_customer:
            raise UserError("Sale order and Tenant database customer should be same !!!")
        ICPSudo = self.env['ir.config_parameter'].sudo()
        print("========ICPSudo=============", ICPSudo)
        brand_website = ICPSudo.search([('key', '=', 'brand_website')]).value
        print("==========brand_website ", brand_website)
        brand_admin = ICPSudo.search([('key', '=', 'admin_login')]).value
        print("==================brand_admin============", brand_admin)
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(brand_website))
        print("==========common=========", common)
        brand_pwd = ICPSudo.search([('key', '=', 'admin_pwd')]).value
        print("=============brand_pwd============", brand_pwd)
        dest_model = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(brand_website))
        print("===========dest_model=============", dest_model)
        trial_days = int(ICPSudo.search([('key', '=', 'free_trial_days')]).value or 0)
        print("=======trial_days=========", trial_days)
        self.action_confirm1()

        #####################################################################
        # Calculate expiry date with selected term , only when the db is paid
        #####################################################################
        total_days = 0
        if self.invoice_ids.payment_state == 'paid':
            if self.invoice_term_id.name == 'Monthly':
                total_days = 30
            elif self.invoice_term_id.name == 'Yearly':
                total_days = 365
            if total_days:
                date = datetime.datetime.now().date()
                db = self.env['tenant.database.list'].sudo().search([('name', '=', self.instance_topup_list.name)])
                db.exp_date = date + datetime.timedelta(days=total_days)

        # print('\n\nUpdating paid db users count after payment')

        ############################################
        # Updating paid db users count after payment
        ############################################
        config_path = self.env['ir.config_parameter'].sudo()
        user_product = config_path.search(
            [('key', '=', 'user_product')]).value
        product = self.env['product.product'].sudo().search([('id', '=', int(user_product))])

        # print("\n\nProduct : ",user_product, product,order,order.invoice_ids,order.invoice_ids.line_ids)

        # tenant_database = self.env['tenant.database.list'].sudo().search([('name','=',self.instance_topup_list.name)])
        # remote_private_url = tenant_database.remote_server_url
        # _logger.info("payment_confirmation_order order>>>>>>>>>>: {},{}".format(remote_private_url,self.is_manage_users))

        if self.is_manage_users:
            _logger.info("creating userrrrrrrrrrr")
            # common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(remote_private_url))
            # dest_model = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(remote_private_url))
            for lines in self.order_line:
                _logger.info(
                    "lines,self.invoice_ids.payment_state>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>{},{},{},{}".format(lines,
                                                                                                            self.order_line,
                                                                                                            product.name,
                                                                                                            lines.name,
                                                                                                            product.display_name))
                # print("\n\nlines : ",lines, self.invoice_ids.payment_state,product)
                _logger.info("\n\n(lines.product_id.name:{}".format(lines.product_id.name))
                _logger.info("\n\n(product.name:{}".format(product.name))
                if (lines.product_id.name == product.name):
                    db = self.env['tenant.database.list'].sudo().search([('name', '=', self.instance_topup_list.name)])
                    db_name = self.instance_topup_list.name
                    _logger.info("payment_confirmation_order db_name >>>>>>>>>>>>>>>>: {}".format(db_name))
                    uid_dst = common.authenticate(db_name, brand_admin, brand_pwd, {})
                    _logger.info("payment_confirmation_order uid_dst >>>>>>>>>>>>>>>>: {}".format(uid_dst))
                    print("\n\n\ndb : ", db, db_name, uid_dst)
                    if db:
                        _logger.info("\n\n\ndb:{}".format(db))
                        for line in self.order_line:
                            if line.product_id.id == product.id:
                                # Modified for billing type
                                _logger.info(
                                    "db.no_of_users$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ {}".format(db.no_of_users))
                                _logger.info("\n\nline.product_uom_qty -111111111 {}".format(line.product_uom_qty))
                                db.no_of_users += line.product_uom_qty
                                _logger.info("\n\nline.product_uom_qty -2222222 {}".format(line.product_uom_qty))
                                _logger.info(
                                    "db.no_of_users,line.product_uom_qty$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ {},{}".format(
                                        db.no_of_users, line.product_uom_qty))
                                users = db.no_of_users
                                _logger.info("users$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ {}".format(users))
                                # print("\n\n\nUsers : ", order.order_line.product_uom_qty,db.no_of_users, users)
                                _logger.info("\n\n\ndb_name------{}>>".format(db_name))
                                _logger.info("\n\n\nuid_dst------{}>>".format(uid_dst))
                                _logger.info("\n\n\ndb_name------{}>>".format(brand_pwd))
                                record = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'saas.service', 'search',
                                                               [[]], {'limit': 1})
                                _logger.info("\n\n\nrecord------{}>>".format(record))
                                result = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'saas.service', 'write',
                                                               [record,
                                                                {
                                                                    'user_count': users
                                                                }]
                                                               )
                                _logger.info("Reuslt----->>: {}".format(result))

        ############################################
        # Updating user database size after payment
        ############################################
        config_path = self.env['ir.config_parameter'].sudo()

        prod = 0
        if self.db_space == True:
            print("============= self.db_space================")
            prod = 1
            db_size_product = config_path.search(
                [('key', '=', 'db_size_usage_product')]).value
        elif self.filestore_space == True:
            print("==========self.filestore_space============")
            prod = 1
            db_size_product = config_path.search(
                [('key', '=', 'filestore_size_usage_product')]).value
        if prod == 1:
            # common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(remote_private_url))
            # dest_model = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(remote_private_url))
            db_product = self.env['product.product'].sudo().search([('id', '=', int(db_size_product))])
            for lines in self.order_line:
                if (db_product.name == lines.product_id.name):
                    db_name = self.instance_topup_list.name
                    uid_dst = common.authenticate(db_name, brand_admin, brand_pwd, {})
                    db = self.env['tenant.database.list'].sudo().search([('name', '=', db_name)])
                    record = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'saas.service', 'search',
                                                   [[]], {'limit': 1})
                    if self.db_space == True:
                        tot_size = db.tenant_db_size + self.order_line.product_uom_qty
                        dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'saas.service', 'write',
                                              [record,
                                               {
                                                   'tenant_db_size': tot_size,

                                               }]
                                              )

                        db.tenant_db_size = tot_size
                    elif self.filestore_space == True:
                        tot_size = db.tenant_filestore_size + self.order_line.product_uom_qty
                        dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'saas.service', 'write',
                                              [record,
                                               {
                                                   'tenant_filestore_size': tot_size,

                                               }]
                                              )
                        db.tenant_filestore_size = tot_size

        for line in self.order_line:
            db_name = self.instance_topup_list.name
            agreement_id = self.env['sale.recurring.orders.agreement'].sudo().search(
                [('instance_name', '=', db_name)])
            if agreement_id:
                _logger.info("\n\n\nagreement_id----------->> :{}".format(agreement_id))
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
                        _logger.info("\n\n\nElseeeeeeeeeeee-----------------222222222222222")
                        values_2 = {
                            'agreement_id': agreement_id.id,
                            'product_id': line.product_id.id,
                            'name': line.product_id.name,
                            'quantity': line.product_uom_qty,
                            'price': lineaction_confirm1.price_unit,
                            'ordering_interval': '1',
                            'ordering_unit': 'years',
                            'createdate': time.strftime('%Y-%m-%d %H:%M:%S'),
                        }

                        self.env['sale.recurring.orders.agreement.line'].sudo().create(
                            values_2)
                    values_3 = {
                        'agreement_id': agreement_id[0].id,
                        'order_id': self.id,
                    }
                    _logger.info("\n\n\n\n\n values_3===================>>>>>>>>>")
                    self.env['sale.recurring.orders.agreement.order'].sudo().create(values_3)
                    # if self.invoice_ids:
                    #     for inv in self.invoice_ids:
                    #         if not inv.agreement_id:
                    #             inv.agreement_id = agreement_id.id

    def create_discounted_invoice(self):
        invoice_line_obj = self.env['account.move.line']
        invoice_obj = self.env['account.move']
        journal_obj = self.env['account.journal']
        today = time.strftime('%Y-%m-%d')
        res = journal_obj.search([('type', '=', 'sale')], limit=1)
        journal_id = res and res[0] or False

        account_id = self.sale_order_ref.partner_id.property_account_receivable_id.id
        invoice_vals = {
            'name': self.name,
            'invoice_origin': self.name,
            'comment': 'SaaS Recurring Invoice',
            'no_of_users': self.no_of_users,
            'invoice_term_id': self.invoice_term_id.id,
            'date_invoice': today,
            'address_invoice_id': self.partner_invoice_id.id,
            'user_id': self._uid,
            'partner_id': self.partner_id.id,
            'account_id': account_id,
            'journal_id': journal_id.id,
            'sale_order_ids': [(4, self.id)],
            'instance_name': str(self.instance_name).encode('utf-8'),
        }
        move_id = invoice_obj.create(invoice_vals)

        for line in self.order_line:
            # print("last price :",line.product_id.lst_price)
            invoice_line_vals = {
                'name': line.product_id.name,
                'invoice_origin': 'SaaS-Kit-' + self.name,
                'move_id': move_id.id,
                'uom_id': line.product_id.uom_id.id,
                'product_id': line.product_id.id,
                'account_id': line.product_id.categ_id.property_account_income_categ_id.id,
                'price_unit': line.product_id.lst_price,
                'discount': 100,
                'quantity': 1,
                'price_subtotal': line.price_subtotal,
                'account_analytic_id': False,
            }
            # print('asdfsafsfsdf',invoice_line_vals)
            if line.product_id.taxes_id.id:
                invoice_line_vals['invoice_line_tax_ids'] = [
                    [6, False, [line.product_id.taxes_id.id]]]  # [(6, 0, [line.product_id.taxes_id.id])],

            invoice_line_obj.create(invoice_line_vals)

            ##make payment paid
            total = move_id.residual
            partner_type = False
            if move_id.partner_id:
                if total < 0:
                    partner_type = 'supplier'
                else:
                    partner_type = 'customer'
            payment_methods = (
                                      total > 0) and self.journal_id.inbound_payment_method_ids or self.journal_id.outbound_payment_method_ids
            currency = self.journal_id.currency_id or self.company_id.currency_id
            payment = self.env['account.payment'].create({
                'payment_method_id': payment_methods and payment_methods[0].id or False,
                'payment_type': total > 0 and 'inbound' or 'outbound',
                'partner_id': self.partner_id and self.partner_id.id or False,
                'partner_type': partner_type,
                'journal_id': self.statement_id.journal_id.id,
                'payment_date': self.date,
                'state': 'reconciled',
                'currency_id': currency.id,
                'amount': abs(total),
                'communication': self._get_communication(payment_methods[0] if payment_methods else False),
                'name': self.statement_id.name,
            })
            payment.action_validate_invoice_payment()

    def create_database_if_not_exist(self, db_name):
        is_created = False
        try:
            exist = False
            ##Check if database name exists in og_database table. Return True if present

            _logger.info('SaaS-Tenant %(db)s creation started' % {'db': db_name})
            self._cr.execute(
                "SELECT u.usename  FROM pg_database d  JOIN pg_user u ON (d.datdba = u.usesysid) WHERE d.datname = '%s'; " % self._cr.dbname)
            current_db_owner = str(self._cr.fetchone()[0])
            self._cr.execute(
                "SELECT u.usename  FROM pg_database d  JOIN pg_user u ON (d.datdba = u.usesysid) WHERE d.datname = 'bare_tenant_17'; ")
            bare_db_owner = str(self._cr.fetchone()[0])
            if current_db_owner != bare_db_owner:
                self._cr.execute('grant "%s" to "%s"' % (bare_db_owner, current_db_owner))
                self._cr.commit()

            self._cr.commit()

            registry = odoo.registry(db_name)

            if current_db_owner != bare_db_owner:
                # if owner not same change owner to current_db_owner
                tables = []
                with closing(registry.cursor()) as tenant_cr:
                    tenant_cr.execute("select tablename from pg_tables where schemaname = 'public'")
                    result = tenant_cr.fetchall()
                    for item in result:
                        if item:
                            tables.append(str(item[0]))
                    tenant_cr.execute(
                        "select sequence_name from information_schema.sequences where sequence_schema = 'public'")
                    result = tenant_cr.fetchall()
                    for item in result:
                        if item:
                            tables.append(str(item[0]))

                    tenant_cr.execute("select table_name from information_schema.views where table_schema = 'public'")
                    result = tenant_cr.fetchall()
                    for item in result:
                        if item:
                            tables.append(str(item[0]))
                    for table in tables:
                        tenant_cr.execute("alter table %s owner to %s" % (table, current_db_owner))
                    tenant_cr.commit()
                    self._cr.execute("revoke %s from %s" % (bare_db_owner, current_db_owner))

        except Exception as e:
            import traceback
            if 'already exists' in str(e):
                raise UserError(_('Database already exist.'))
            else:
                raise UserError(_('Error\n %s') % str(e))
        return is_created

    def send_db_creation_mail(self, db_name):

        ##Send DB creation mail
        email_template_obj = self.env['mail.template']

        _logger.info('\n\nmail template object {}'.format(email_template_obj))
        mail_template_id = self.env['ir.model.data']._xmlid_to_res_id(
            'saas_sale.email_template_database_creation')

        _logger.info('\n\nmail ID {}'.format(mail_template_id))
        email_template_obj.browse(int(mail_template_id)).send_mail(self.id, force_send=True)

        _logger.info('\n\nmail Sent')
        _logger.info('\n\nTenant %(db_name)s is created successfully' % {'db_name': db_name})

    def post_installation_work(self, module_list):
        print("\n\n-----------------------------------------------------------------")
        print("Post Installation Work Started")
        for rec in self:
            try:
                order = self
                queue_job_ids = self.env['queue.job'].search([('db_name', '=', order.instance_name)], order="id asc")
                if queue_job_ids:
                    count = 0
                    for job in queue_job_ids:
                        if job.state == 'failed':
                            count += 1
                        if count > 0:
                            raise UserError(_("Previous Dependent Job {} Is Failed!".format(job.tenant_name)))
                    if count > 0:
                        return 0
            except Exception as e:
                msg = str(e) or ''
                if msg == "'queue.job'":
                    continue
                else:
                    raise UserError(_("Previous Dependent Job Is Failed!"))
        tenant_database_list_obj = self.env['tenant.database.list'].sudo()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        db_size = ICPSudo.search([('key', '=', 'tenant_db_size')]).value
        filestore_size = ICPSudo.search([('key', '=', 'tenant_filestore_size')]).value
        brand_name = ICPSudo.search([('key', '=', 'brand_name')]).value
        brand_website = ICPSudo.search([('key', '=', 'brand_website')]).value
        brand_admin = ICPSudo.search([('key', '=', 'admin_login')]).value
        brand_pwd = ICPSudo.search([('key', '=', 'admin_pwd')]).value
        if not self.is_top_up:
            db_name = str(order.instance_name).lower().replace(" ", "_")
            order.instance_name = db_name
        else:
            db_name = order.instance_topup_list.name
        # db_name = str(order.instance_name).lower().replace(" ", "_")
        # order.instance_name = db_name
        admin_login = str(ICPSudo.search([('key', '=', 'admin_login')]).value) or 'admin'
        admin_pwd = str(ICPSudo.search([('key', '=', 'admin_pwd')]).value) or 'admin'
        print('\n\nDatabase Name %s', db_name)
        print('\n\nDatabase size %s', db_size)
        print('\n\nDatabase filestore_size %s', filestore_size)
        print('\n\nDatabase brand_website %s', brand_website)
        print('\n\nDatabase Name %s', db_name)
        order_date = datetime.datetime.strptime(str(datetime.date.today()), '%Y-%m-%d')
        print("\n\n0000000000000000000000000000000000000000000000000000000000000000000000\n\n")
        if order.invoice_ids.payment_state == 'paid':
            if order.invoice_term_id.type == 'year':
                free_trial_days = 365
            else:
                free_trial_days = 30
        else:
            if order.invoice_term_id.type == 'year':
                free_trial_days = int(ICPSudo.search(
                    [('key', '=', 'free_trial_days')]).value) or 365
            else:
                free_trial_days = int(ICPSudo.search(
                    [('key', '=', 'free_trial_days')]).value) or 30
        print("free_trial_days:::::::::", free_trial_days)
        exp_date = str(order_date + datetime.timedelta(days=free_trial_days))[:10]
        print("exp_date:::::::::", exp_date)
        new_user_id = False
        psuedo_user_pwd = self.random_password()
        dest_model = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(brand_website))
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(brand_website))
        print('\n\nDest Model %s', dest_model)
        print('\n\ncommon %s', common)
        print('\n\nDB NAME %s', db_name)
        print('\n\nbrand_pwd %s', brand_pwd)
        # _logger.info('\n\nsudo_pwd %s', psuedo_user_pwd)
        uid_dst = common.authenticate(db_name, admin_login, brand_pwd, {})
        print('\n\nuid_dst %s', uid_dst)
        if not uid_dst:
            print("Entered if not uid_dst")
            uid_dst = common.authenticate(db_name, 'admin', 'admin', {})
            brand_pwd = 'admin'
        print("uid_dst::::::::::", uid_dst)
        print("brand_pwd::::::::::", brand_pwd)
        print("\n\n11111111111111111111111111111111111111111111111111111111111111111")
        if uid_dst:

            ############################################################################################
            # Install Selected language
            #############################################################################################

            if self.tenant_language:
                _logger.info('\n\nInstalling Language {} in tenant {}'.format(self.tenant_language.name,
                                                                              self.tenant_language.code))

                res_lang_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.lang', 'search',
                                                     [[['code', 'ilike', self.tenant_language.code],
                                                       ['active', 'in', [True, False]]]])

                dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.lang', 'write',
                                      [res_lang_ids,
                                       {
                                           'active': True,
                                       }]
                                      )

                _logger.info(
                    '\n\nInstalling Language {} found in tenant with id {}'.format(self.tenant_language.name,
                                                                                   res_lang_ids))
                if res_lang_ids:
                    lang_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.lang',
                                                     'install_language', [res_lang_ids])
                    if lang_ids:
                        _logger.info('\n\nInstalling Language {} in tenant {} Successful'.format(
                            self.tenant_language.name, db_name))
                    else:
                        _logger.warning('\n\nInstalling Language {} not found in tenant {}'.format(
                            self.tenant_language.name, db_name))
                else:
                    _logger.warning(
                        '\n\nLanguage {} not found in tenant {}'.format(self.tenant_language.name, db_name))
            #############################################################################################
            _logger.info("credes for new user id >>>>>>>>>>>{}>>>>>>>>>{}>>>>>>>>>>{}".format(order.partner_id.email,
                                                                                              order.partner_id.name,
                                                                                              psuedo_user_pwd))
            # start
            product = self.order_line.product_template_id
            user = product.related_database.sale_order_ref.partner_id.email
            print("============useruseruseruseruser====================", user)
            all_user = self.env['res.users'].search([])
            user_id = self.env['res.users'].search([('login', '!=', user), ('id', '!=', 2)])
            print("===========product.related_database==============", product.related_database)
            if product.related_database:
                rec_user = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'search',
                                                 [[['login', '=', user]]])
                print("================dfsdnflkdslsjdlsjdlasjlaj=====")
                user_to_remove = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'search',
                                                       [[['login', '!=', user], ['id', '!=', 2]]])
                dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'unlink', [user_to_remove])
                new_user_id = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'write',
                                                    [rec_user,
                                                     {
                                                         'login': order.partner_id.email,
                                                         'name': order.partner_id.name,
                                                         'password': psuedo_user_pwd,
                                                         #  'lang': self.tenant_language.code,
                                                     }]
                                                    )

                record_id = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'db.expire', 'search', [[]])
                dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'db.expire', 'write',
                                      [record_id, {'db_expire': False}])

            # end

            if not product.related_database:
                print("===========order.partner_id.email===========", order.partner_id.email)
                print("==========order.partner_id.name======", order.partner_id.name)
                print("==========psuedo_user_pwd======", psuedo_user_pwd)
                print("================", db_name, uid_dst, brand_pwd)

                new_user_id = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'copy',
                                                    [2,
                                                     {
                                                         'login': order.partner_id.email,
                                                         'name': order.partner_id.name,
                                                         'password': psuedo_user_pwd,
                                                         #  'lang': self.tenant_language.code,
                                                     }]
                                                    )
                print("===============new_user_id==========================", new_user_id)

                dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'write',
                                      [new_user_id,
                                       {
                                           'active': 't',
                                       }]
                                      )

            dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'write',
                                  [2,
                                   {
                                       'password': brand_pwd or 'admin',
                                       'login': admin_login or 'admin',
                                   }]
                                  )
            if product.related_database:
                records = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'saas.service', 'search',
                                                [[]])

                deleted_records = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'saas.service', 'unlink',
                                                        [records])
            dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'saas.service', 'create',
                                  [{
                                      'use_user_count': 1,
                                      'user_count': order.no_of_users,
                                      'name': db_name,
                                      'expiry_date': exp_date,
                                      'tenant_db_size': db_size,
                                      'tenant_filestore_size': filestore_size,
                                  }]
                                  )

            if not product.related_database:
                group_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.groups', 'search',
                                                  [[('name', '=', 'My Service Access')]])
                print("group_ids::::::::::::", group_ids)
                for group_id in group_ids:
                    dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'write',
                                          [new_user_id,
                                           {
                                               'tenant_user': True,
                                               'in_group_' + str(group_id): True if group_id else '',
                                           }]
                                          )

                # CHANGE_ODOO_LABELS_TO_BRAND_NAME
                tenant_msg_id = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'mail.message', 'search',
                                                      [[('subject', '=', 'Welcome to Odoo!')]])
                for msg in tenant_msg_id:
                    dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'mail.message', 'write',
                                          [msg,
                                           {
                                               'subject': 'Welcome to %s!' % brand_name,
                                           }]
                                          )

        ##Create Tenant Database List Record
        print("Creating tenant db record::::::::::::::::::::;")
        stage_ids = self.env['tenant.database.stage'].search([('is_active', '=', True)])
        print("\n\nTenant database list creating\n\n", stage_ids)
        tenant_database_list_vals = {
            'name': db_name,
            'exp_date': exp_date,
            'free_trial': order.free_trial,
            'sale_order_ref': order.id,
            'no_of_users': order.no_of_users,
            'invoice_term_id': order.invoice_term_id.id,
            'stage_id': stage_ids.id if stage_ids else False,
            'user_pwd': psuedo_user_pwd,
            # 'user_login': db_name,
            'billing': order.billing,
            'super_user_login': admin_login,
            'super_user_pwd': brand_pwd,
            'user_login': order.customer_email or order.partner_id.email
        }
        tenant_database_id = tenant_database_list_obj.create(tenant_database_list_vals)
        print("\nTEnant db list Created:::::", tenant_database_id)

        ##To check Enable password reset from login page
        dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.config.settings', 'create',
                              [{'auth_signup_reset_password': True, }])

        ## SET TENANT SUPER USER GROUP TO SUPERADMIN USER
        ## COPY ALL ACCESS RIGHTS AND SET THEM A PSUEDO ADMIN GROUP
        if not product.related_database:
            group_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.groups', 'search',
                                              [[
                                                  '|', '|',
                                                  ['name', '=', 'My Service Access'],
                                                  ['name', '=', 'Technical Features'],
                                                  ['name', '=', 'Tenant Super User'],
                                              ]]
                                              )
            for group in group_ids:
                try:
                    dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'perform_many2many_table_work2',
                                          [2],
                                          {'group_id': group})
                except Exception as e:
                    print(e)

            ## SET GOUPS_ID TO FALSE IN 'IR_UI_MENU'
            menu_id = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.ui.menu', 'search',
                                            [[
                                                ('complete_name', '=', 'Settings/Translations/Languages'),
                                                ('name', '=', 'Languages')
                                            ]])
            if menu_id:
                group_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.groups', 'search',
                                                  [[
                                                      ('full_name', '=', 'Settings/Translations/Languages'),
                                                      ('name', '=', 'Languages')
                                                  ]])

                groups_ids_menu = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users',
                                                        'perform_many2many_table_work_browse1', [2],
                                                        {'menu_id': menu_id})

                groups_ids = set(groups_ids_menu) - set(group_ids)

                if groups_ids:
                    groups_ids = list(groups_ids)
                else:
                    groups_ids = []

                dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.ui.menu', 'write',
                                      [menu_id,
                                       {
                                           'groups_id': [(6, False, groups_ids)]
                                       }]
                                      )

            ## GIVE ALL AVAILABLE RIGHTS
            if not product.related_database:
                if new_user_id:
                    technical_settings_id = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.module.category',
                                                                  'search',
                                                                  [[
                                                                      '|',
                                                                      ['name', '=', 'technische instellingen'],
                                                                      ['name', '=', 'Technical Settings'],
                                                                  ]])

                    group_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.groups', 'search',
                                                      [[
                                                          '|', '|',
                                                          ['category_id', '=', 'technical_settings_id'],
                                                          ['name', '=', 'Employee'],
                                                          ['name', '=', 'Psuedo Admin']
                                                      ]])

                    for group_id in group_ids:
                        dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'perform_many2many_table_work3',
                                              [2],
                                              {'group_id': group_id, 'new_user_id': new_user_id})
            if not product.related_database:
                ## REMOVE TENANT SUPER USER RIGHT FROM ALL TENANT USERS
                tenant_settings_group_id = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.groups', 'search',
                                                                 [[
                                                                     ('name', '=', 'Tenant Super User')
                                                                 ]])

            for id in tenant_settings_group_id:
                tenant_user_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'search',
                                                        [[('id', '>', 2)]])
                for user in tenant_user_ids:
                    dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'perform_many2many_table_work5',
                                          [2],
                                          {'group_id': id, 'user_id': user})

            ## HIDING ALL ODOO WORDS from ACTIONS
            action_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.actions.act_window', 'search',
                                               [[]])

            for action in action_ids:
                help = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users',
                                             'perform_many2many_table_work_browse2', [2],
                                             {'act_id': action})

                dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.actions.act_window', 'write',
                                      [action,
                                       {
                                           'help': str(help or '').replace('Odoo', brand_name)
                                       }]
                                      )

            # installing custom modules
            self.sudo().action_install_module(db_name, module_list)
            print(module_list, ":::::::::: Done")
        # WRITE TENANT USER PWD IN SO TO SEND IT IN A MAIL TO USER
        self.pwd = psuedo_user_pwd
        self = self.with_user(SUPERUSER_ID)
        self.sudo().send_db_creation_mail(db_name)
        _logger.info("send mail sudo >>>>>>>>>>.")
        _logger.info("send mail sudo >>>>>>>>>>.{}".format(self.env.su))
        # ------------End-------------------------

    def is_tenant_created(self):
        db_name = self.instance_name
        self._cr.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
        db_names = self._cr.fetchall()
        _logger.info("\n\ntenant database name : {}".format(db_name))
        exist = False
        for item in db_names:
            print('\n\ndatabase\n_______', item)
            if item:
                if db_name == str(item[0]):
                    print('\n\nDatabase matched ', item[0], db_names)
                    exist = True
        _logger.info("\n\ntenant database is exist? : {}".format(exist))
        return exist

    def create_database(self, module_list):
        db_name = self.instance_name
        ICPSudo = self.env['ir.config_parameter'].sudo()
        # print(config['bare_db'], '_______________________________config')
        # db.exp_duplicate_database(config['bare_db'], db_name)
        _logger.info("\n\n............before duplicate database...............")
        product = self.order_line.product_template_id
        database_name = product.related_database.name
        if product.related_database:
            bare_db = str(database_name)
            try:
                new_db = db.exp_duplicate_database(bare_db, db_name)

            except Exception as e:
                print("EXception in duplicating db:::", e)
        else:
            bare_db = str(ICPSudo.search([('key', '=', 'bare_tenant_db')]).value) or 'bare_tenant_17'
            try:
                new_db = db.exp_duplicate_database(bare_db, db_name)

            except Exception as e:
                raise UserError(_("EXception in duplicating db", e))
                print("EXception in duplicating db:::", e)
        # print("new db::::::::::::", new_db)
        _logger.info("\n\n............after duplicate database...............")
        # ===================================================================
        # Change admin password of tenant database as per configured in SaaS Configuration.
        # ===================================================================
        registry = odoo.registry(db_name)
        # tenant_db = odoo.sql_db.db_connect(db_name)
        # tenant_cr = tenant_db.cursor()
        brand_admin = ICPSudo.search([('key', '=', 'admin_login')]).value
        admin_pwd = ICPSudo.search([('key', '=', 'admin_pwd')]).value
        print("Registry:::::::::::", registry)
        # print("tenant_db:::::::::::", tenant_db)
        # print("tenant_cr:::::::::::", tenant_cr)
        print("brand_admin:::::::::::", brand_admin)
        print("admin_pwd:::::::::::", admin_pwd)
        with registry.cursor() as cr:
            print("ins:::::::::::")
            env = Environment(cr, ADMINUSER_ID, {})
            print("env:::::::::::", env)
            env['res.users'].browse(2).sudo().write({'login': brand_admin})
            print("eeeee:::::::::::")
            cr.commit()
            print("ssss:::::::::::")
            if admin_pwd:
                env['res.users'].browse(2).sudo().write({'password': admin_pwd})
                cr.commit()
                print("ddd:::::::::::")
            else:
                env['res.users'].browse(2).sudo().write({'password': 'admin'})
                cr.commit()
        print("::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::\n\n")
        print("\nModule installation started")
        print("db_name:::::::", db_name)

        try:
            self.action_install_module(db_name, ['sales_team', 'openerp_saas_tenant'])
            self.sudo().action_install_module(db_name, module_list)
            print("['sales_team', 'openerp_saas_tenant']:::::::::: Done")
            self.action_install_module(db_name, ['sale_group', 'db_filter'])
            print("['sale_group', 'db_filter']:::::::::: Done")
            self.action_install_module(db_name, ['openerp_saas_tenant_extension', 'web_saas'])
            print("['openerp_saas_tenant_extension', 'web_saas']:::::::::: Done")
            self.action_install_module(db_name, ['openerp_saas_tenant_account', 'contacts', 'openerp_dashboard'])
            print("['openerp_saas_tenant_account', 'contacts']:::::::::: Done")

        except Exception as e:
            print("Exception::::::::::1111111111111111", e)
        print("\n\n::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::")
        _logger.info('\n\nAdded record in Saasmaster to access tenant Info\n\n')

    def post_database_update(self, module_list):
        _logger.info("post_database_update----------------------------------")
        for rec in self:
            try:
                order = self
                queue_job_ids = self.env['queue.job'].search([('db_name', '=', order.instance_name)], order="id asc")
                if queue_job_ids:
                    count = 0
                    for job in queue_job_ids:
                        if job.state == 'failed':
                            count += 1
                        if count > 0:
                            raise UserError(_("Previous Dependent Job {} Is Failed!".format(job.tenant_name)))
                    if count > 0:
                        return 0
            except Exception as e:
                msg = str(e) or ''
                if msg == "'queue.job'":
                    continue
                else:
                    raise UserError(_("Previous Dependent Job Is Failed!"))
        name_module = None
        for line in self.order_line:
            for list_module in line.product_id.product_tmpl_id.module_list:
                name_module = list_module.name
            if name_module:
                if name_module == 'account':
                    if self.partner_id.country_id:
                        module = self.env['ir.module.module'].sudo().search(
                            [('name', '=', 'l10n_%s' % self.partner_id.country_id.code.lower())])
                    elif self.company_id.country_id:
                        module = self.env['ir.module.module'].sudo().search(
                            [('name', '=', 'l10n_%s' % self.company_id.country_id.code.lower())])
                    if module:
                        accounting_module = module.name

                    if accounting_module:
                        self.action_install_module(db_name, [accounting_module])
        for sale_order_object in self:
            sale_recurring_order_obj = self.env['sale.recurring.orders.agreement'].sudo()
            recurring_order_rel_obj = self.env['sale.recurring.orders.agreement.order']

            # db_name = self.instance_name
            if not self.is_top_up:
                db_name = str(order.instance_name).lower().replace(" ", "_")
                order.instance_name = db_name
            else:
                db_name = order.instance_topup_list.name
            ICPSudo = self.env['ir.config_parameter'].sudo()
            brand_website = ICPSudo.search([('key', '=', 'brand_website')]).value
            total_days = ICPSudo.search([('key', '=', 'free_trial_days')]).value or 30
            brand_admin = ICPSudo.search([('key', '=', 'admin_login')]).value
            admin_pwd = ICPSudo.search([('key', '=', 'admin_pwd')]).value
            brand_pwd = ICPSudo.search([('key', '=', 'admin_pwd')]).value

            dest_model = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(brand_website))
            common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(brand_website))
            uid_dst = common.authenticate(db_name, brand_admin, brand_pwd, {})

            # =======================================================================
            # 'from_existed_agreement' : Agreement will create first time only if the order is related to Saas products
            # =======================================================================
            ## TODO:" check agreement is already created for this order
            agreement = recurring_order_rel_obj.sudo().search([('order_id', '=', sale_order_object.id)])

            if not agreement:

                if sale_order_object.instance_name or sale_order_object.instance_topup_list:
                    recurring_order_name = 'SaaS-' + sale_order_object.name

                    date_time = time.strftime("%d") + '/' + time.strftime("%b") + '/' + time.strftime(
                        "%Y") + ' ' + time.strftime("%X")
                    agreement_id = None

                    if not sale_order_object.is_top_up:
                        start_date = sale_order_object.date_order
                        end_date = start_date + datetime.timedelta(days=int(total_days))

                        agreement_vals = {
                            'state': 'first',
                            'name': recurring_order_name,
                            'partner_id': sale_order_object.partner_id.id,
                            'start_date': start_date,
                            'company_id': sale_order_object.company_id.id,
                            'end_date': end_date,
                            'billing': sale_order_object.billing,
                            'version_no': '1.1',
                            'log_history': date_time + ' :- Agreement is created',
                            'invoice_term_id': sale_order_object.invoice_term_id.id,
                            'instance_name': str(sale_order_object.instance_name).encode('utf-8'),
                            'active': True,
                        }
                        agreement_id = sale_recurring_order_obj.sudo().create(agreement_vals)
                    else:
                        ## XMLRPC
                        last_group_id = max(
                            dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.groups', 'search', [[]]))
                        last_access_control_id = max(
                            dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.model.access', 'search', [[]]))

                        for x in module_list:
                            self.action_install_module(self.instance_topup_list.name, [x])

                        group_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.groups', 'search',
                                                          [[['id', '>', last_group_id]]])
                        user_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'search', [[]])
                        for user in user_ids:
                            if group_ids:
                                for group in group_ids:
                                    dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'write',
                                                          [user,
                                                           {
                                                               'in_group_' + str(group): True if group else ''
                                                           }]
                                                          )
                                # user.write({'in_group_' + str(group.id):True if group else '',})

                        group_id = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.groups', 'search',
                                                         [[['name', '=', 'Tenant Super User']]])
                        if group_id:
                            access_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.model.access', 'search',
                                                               [[['id', '>', last_access_control_id]]])
                            for access_id in access_ids:
                                try:
                                    new_access_id = dest_model.execute_kw(db_name, uid_dst, brand_pwd,
                                                                          'ir.model.access', 'copy',
                                                                          [access_id,
                                                                           {

                                                                           }]
                                                                          )
                                    for group in group_id:
                                        dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.model.access', 'write',
                                                              [new_access_id,
                                                               {
                                                                   'group_id': group,
                                                                   'perm_unlink': 't',
                                                                   'perm_write': 't',
                                                                   'perm_create': 't',
                                                                   'perm_read': 't',
                                                               }]
                                                              )
                                except Exception as e:
                                    print(e)

                        ## If sale_order is top-up order don't create new agreement.
                        ## Instead of this use existing agreement and update it with new sale_order and product line
                        agreement_id = self.env['sale.recurring.orders.agreement'].sudo().search(
                            [('partner_id', '=', sale_order_object.partner_id.id),
                             ('active', '=', True),
                             ('instance_name', '=', sale_order_object.instance_topup_list.name)])

                    # ===========================================================
                    # Check if product is bundle product or simple product
                    # If product is bundle product, line 'sale_recurring_order_line_obj'
                    # will contain all bundle products and main product
                    # ===========================================================
                    for line in sale_order_object.order_line:
                        # ===========================================================
                        # Add main product also
                        # ===========================================================

                        values_2 = {
                            'agreement_id': agreement_id[0].id,
                            'product_id': line.product_id.id,
                            'name': line.product_id.name,
                            'quantity': line.product_uom_qty,
                            'price': line.price_unit,
                            'ordering_interval': '1',
                            'ordering_unit': 'years',
                            'createdate': time.strftime('%Y-%m-%d %H:%M:%S'),
                        }

                        self.env['sale.recurring.orders.agreement.line'].sudo().create(values_2)

                    ## write sale order reference in agreement
                    values_3 = {
                        'agreement_id': agreement_id[0].id,
                        'order_id': sale_order_object.id,
                    }
                    self.env['sale.recurring.orders.agreement.order'].sudo().create(values_3)
                    if order.invoice_ids:
                        for inv in order.invoice_ids:
                            if not inv.agreement_id:
                                inv.agreement_id = agreement_id.id

                partner_id = self.env['res.partner'].sudo().search([('id', '=', order.partner_id.id)])
                automated = request.env['ir.config_parameter'].sudo().get_param('billing_type_extension.automated')
                db_creation = bool(automated)
                if db_creation:
                    partner_id.seq_no += 1

    def action_confirm1(self):
        print("=========action_confirm1=========", self)
        for sale in self.sudo().search(['&', ('state', 'not in', ['draft', 'cancel']), ('id', '!=', self.id)]):
            _logger.info('=======Checking Sale order Name : {}'.format(sale.name))
            if sale.instance_name and sale.instance_name == self.instance_name and not self.is_top_up and self.saas_order:
                raise ValidationError("Instance Name Is Already Exist! Please Try Different Name!")
        _logger.info('\n\nInside Action Confirm Method ...........')
        # =======================================================================
        # call super of sale order to generate sales order
        # =======================================================================
        ICPSudo = self.env['ir.config_parameter'].sudo()
        buy_product_id = int(ICPSudo.search([('key', '=', 'buy_product')]).value or False)
        brand_website = ICPSudo.search([('key', '=', 'brand_website')]).value
        brand_admin = ICPSudo.search([('key', '=', 'admin_login')]).value
        brand_pwd = ICPSudo.search([('key', '=', 'admin_pwd')]).value
        total_days = ICPSudo.search([('key', '=', 'free_trial_days')]).value or 30
        print("buy_product_id::::::::::::::::::", buy_product_id)
        print("brand_website::::::::::::::::::", brand_website)
        print("brand_admin::::::::::::::::::", brand_admin)
        print("brand_pwd::::::::::::::::::", brand_pwd)
        print("total_days::::::::::::::::::", total_days)
        if not brand_admin:
            raise UserError('Please Configure SaaS Settings')

        partner = self.partner_id
        country = partner.country_id
        accounting_module = ''
        name_module = False
        print("partner::::::::::::::::::", partner)
        print("country::::::::::::::::::", country)

        # if self.state not in ['sent', 'draft']:
        #     return True
        if not self.saas_order:
            _logger.info("if not self.saas_order-----------------")
            return self.action_confirm()

        if not self._context: conText = {}
        module_list = []
        if self.saas_order and not self.instance_name and not self.is_top_up:
            raise UserError('Please provide Instance Name!')
        self = self.sudo()
        if self.order_line:
            for line in self.order_line:
                if line.product_id.is_saas and line.product_id != buy_product_id:
                    if line.product_id.product_tmpl_id.module_list:
                        module_list += [m.name for m in line.product_id.product_tmpl_id.module_list]
        # if 'website' in module_list:
        db_name = self.instance_name
        if self.is_top_up:
            db_name = self.instance_topup_list.name
        else:
            db_name = self.instance_name
        _logger.info('Module to be install on tenant database %(db)s started ' % {'db': str(module_list)})
        # =======================================================================
        # create tenant database and record and install modules
        # =======================================================================
        # tenant_db_obj = self.env['tenant.database.list'].sudo().search([('name', '=', self.instance_name)])
        # if tenant_db_obj:
        #     raise UserError("Database already available")

        transaction = self.env['payment.transaction']

        if self.saas_order:
            ## create new user with name tenant name
            ## Auto install "web_adblock" to tenant DB
            # module_list.append('web_adblock')
            # self._cr.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")

            # db_names = self._cr.fetchall()
            exist = False
            # for item in db_names:
            #     if item:
            #         if db_name == str(item[0]):
            #             exist = True
            #             if not self.is_top_up:
            #                 _logger.info('\n\nDatabase is already exist : {}\n\n'.format(db_name))
            #                 raise UserError(_('Database "%s" is already exists...!' % db_name))
            #             else:
            #                 break

            if not exist:
                _logger.info("datbase creation through create instance")
                try:
                    self.with_delay().create_database(module_list)
                except Exception as e:
                    msg = str(e) or ''
                    if msg == "'sale.order' object has no attribute 'with_delay'":
                        self.create_database(module_list)
                    else:
                        raise UserError('Exception while creating container : {} '.format(e))
                try:
                    self.with_delay().post_installation_work(module_list)
                except Exception as e:
                    msg = str(e) or ''
                    if msg == "'sale.order' object has no attribute 'with_delay'":
                        self.post_installation_work(module_list)
                    else:
                        raise UserError('Exception while creating database : {} '.format(e))

            # if self.is_top_up:
            #     self.sudo().action_install_module(db_name, module_list)

        res =  self.action_confirm()

        if self.is_top_up:
            self.post_database_update(module_list)
        else:
            try:
                self.with_delay().post_database_update(module_list)
            except Exception as e:
                msg = str(e) or ''
                if msg == "'sale.order' object has no attribute 'with_delay'":
                    self.post_database_update(module_list)
                else:
                    raise UserError('Exception while installing modules : {} '.format(e))

                # self.env.cr.execute("INSERT INTO sale_recurring_orders_agreement_order(agreement_id, order_id) VALUES (%s, %s)" % (agreement_id.id,sale_order_object.id))

        #                 self.env['sale.recurring.orders.agreement.line'].sudo().create(values_2)

        #             ## write sale order reference in agreement
        #             values_3 = {
        #                 'agreement_id': agreement_id[0].id,
        #                 'order_id': sale_order_object.id,
        #             }
        #             self.env['sale.recurring.orders.agreement.order'].sudo().create(values_3)
        #             # self.env.cr.execute("INSERT INTO sale_recurring_orders_agreement_order(agreement_id, order_id) VALUES (%s, %s)" % (agreement_id.id,sale_order_object.id))
        return res

    def create_first_invoice(self):
        invoice_line_obj = self.env['account.move.line']
        invoice_obj = self.env['account.move']
        journal_obj = self.env['account.journal']
        today = time.strftime('%Y-%m-%d')
        move_id = None
        res = journal_obj.search([('type', '=', 'sale')], limit=1)
        journal_id = res and res[0] or False
        account_id = self.partner_id.property_account_receivable_id.id
        invoice_vals = {
            'name': self.name,
            'invoice_origin': self.name,
            'comment': 'First Invoice',
            'date_invoice': today,
            'address_invoice_id': self.partner_invoice_id.id,
            'user_id': self._uid,
            'partner_id': self.partner_id.id,
            'no_of_users': self.no_of_users,
            'invoice_term_id': self.invoice_term_id.id,
            'account_id': account_id,
            'journal_id': journal_id.id,
            'sale_order_ids': [(4, self.id)],
            'instance_name': str(self.instance_name).encode('utf-8'),
        }
        move_id = invoice_obj.create(invoice_vals)

        ## make invoice line from the agreement product line
        for line in self.order_line:
            qty = line.product_uom_qty
            # print("last price 222222222:", line.product_id.lst_price)
            invoice_line_vals = {
                'name': line.product_id.name,
                'invoice_origin': self.name,
                'move_id': move_id.id,
                'uom_id': line.product_id.uom_id.id,
                'product_id': line.product_id.id,
                'account_id': line.product_id.categ_id.property_account_income_categ_id.id,
                'price_unit': line.product_id.lst_price,
                'discount': line.discount,
                'quantity': qty,
                'price_subtotal': line.price_subtotal,
                'account_analytic_id': False,
            }
            if line.product_id.taxes_id.id:
                invoice_line_vals['invoice_line_tax_ids'] = [
                    [6, False, [line.product_id.taxes_id.id]]]  # [(6, 0, [line.product_id.taxes_id.id])],

            invoice_line_obj.create(invoice_line_vals)

        # recompute taxes(Update taxes)
        return move_id

    def _prepare_invoice(self):
        _logger.info("\n----------------------_prepare_invoice-----------------------\n")
        invoice_vals = super(sale_order, self)._prepare_invoice()
        invoice_vals[
            'instance_name'] = self.instance_topup_list.name if self.instance_topup_list.name else self.instance_name
        invoice_vals['no_of_users'] = self.no_of_users
        invoice_vals['invoice_term_id'] = self.invoice_term_id.id
        invoice_vals['saas_order'] = self.saas_order
        agreement_id = self.env['sale.recurring.orders.agreement'].sudo().search(
            [('instance_name', '=',
              self.instance_topup_list.name if self.instance_topup_list.name else self.instance_name)])
        _logger.info("agreement_id-Name--------->>>{}".format(agreement_id.name))
        _logger.info("agreement_id---------->>>{}".format(agreement_id))
        _logger.info("agreement_id.id--------->>>{}".format(agreement_id.id))
        invoice_vals['agreement_id'] = agreement_id.id
        _logger.info("invoice_vals['agreement_id']: {}".format(invoice_vals['agreement_id']))
        _logger.info("invoice_vals------------>>{}".format(invoice_vals))
        return invoice_vals

    @api.depends('order_line.tax_id', 'order_line.price_unit', 'amount_total', 'amount_untaxed')
    def _compute_tax_totals_json(self):
        # res = super(sale_order, self)._compute_tax_totals_json()

        def compute_taxes(order_line):
            price = order_line.price_unit * (1 - (order_line.discount or 0.0) / 100.0)
            order = order_line.order_id
            if self.billing == 'normal':
                qty = order_line.product_uom_qty * self.no_of_users * order_line.month
            else:
                qty = order_line.product_uom_qty * order_line.month

            return order_line.tax_id._origin.compute_all(price, order.currency_id, qty, product=order_line.product_id,
                                                         partner=order.partner_shipping_id)

        account_move = self.env['account.move']
        for order in self:
            tax_lines_data = account_move._prepare_tax_lines_data_for_totals_from_object(order.order_line,
                                                                                         compute_taxes)
            # print("\n\n---------------------\n", tax_lines_data, "\n")
            # print("amount tota;:::", order.amount_total)
            tax_totals = account_move._get_tax_totals(order.partner_id, tax_lines_data, order.amount_total,
                                                      order.amount_untaxed, order.currency_id)
            # print("tax totalssssss::::::", tax_totals)
            order.tax_totals_json = json.dumps(tax_totals)
        # return res

    @api.onchange('instance_name')
    def _onchange_instance_name(self):
        for rec in self:
            if rec.instance_name:
                string_to_check = rec.instance_name
                contains_uppercase = any(char.isupper() for char in string_to_check)
                if contains_uppercase:
                    raise ValidationError(_("UpperCase Letter Is Not Allowed In Instance Name!!"))
                regex = re.compile('[@!#$%^&*()<>?/\|}{~:-=+`]')
                if (regex.search(string_to_check) != None):
                    raise ValidationError(_("Special Symbols Are Not Allowed In Instance Name!!"))

    def convert_to_english(self, phone_number):
        """
        Convert the phone number from Arabic digits to English digits.
        Args:
            phone_number (str): The phone number to convert.
        Returns:
            str: The phone number with English digits.
        """
        # Define a mapping dictionary for Arabic to English digits
        arabic_to_english = {
            '٠': '0',
            '١': '1',
            '٢': '2',
            '٣': '3',
            '٤': '4',
            '٥': '5',
            '٦': '6',
            '٧': '7',
            '٨': '8',
            '٩': '9',
        }

        # Loop through each character in the phone number and replace Arabic digits with English digits
        english_number = ''
        for char in phone_number:
            # If the character is an Arabic digit, replace it with the corresponding English digit
            if char in arabic_to_english:
                english_number += arabic_to_english[char]
            else:
                english_number += char

        return english_number

    @api.onchange('partner_id', 'saas_order')
    def _onchange_partner_id_database_name(self):
        if self.saas_order:
            automated = request.env['ir.config_parameter'].sudo().get_param('billing_type_extension.automated')
            print("============automated=============", automated)
            based_on = request.env['ir.config_parameter'].sudo().get_param('billing_type_extension.based_on')
            print("============based_on==============", based_on)
            # order = self.env['sale.order'].sudo().search([('id', '=', self)])
            # partner = self.env['res.partner'].sudo().search([('id', '=', self.partner_id)])

            if automated and based_on == 'phone_number':
                for rec in self:
                    if rec.partner_id:
                        # tenanat_list = request.env["tenant.database.list"].sudo().search([('name', '=', str(rec.partner_id.phone))])
                        tenanat_list = request.env["tenant.database.list"].sudo()
                        # if not tenanat_list:

                        phone_code = '+' + str(rec.partner_id.country_id.phone_code)
                        for char in rec.partner_id.phone:
                            phone_number = str(rec.partner_id.phone)
                            if char in '٠١٢٣٤٥٦٧٨٩':
                                phone_number = self.convert_to_english(phone_number)

                        phone = str(phone_number)
                        instance_name = ""
                        if phone_code in phone:
                            if phone_code != '0' and phone:
                                instance_name = phone.replace(phone_code, "", ).replace("+", "").replace(' ', "")

                            elif phone_code == '0' and phone:
                                instance_name = phone.replace("+", "").replace(' ', "")
                            else:
                                instance_name = str(phone).replace("+", "").replace(' ', "")
                        else:
                            instance_name = phone

                        inst_name = instance_name.replace(' ', "").replace('+', '')

                        # rec.instance_name = str(instance_name)
                        tenant_name, sequence_number = tenanat_list.check_sequence_number(instance_name=inst_name,
                                                                                          sequence_no=1,
                                                                                          old_instance_name=inst_name)
                        tenant, seq_number = tenanat_list.check_phone_number(sequence_no=sequence_number,
                                                                             instance_name=instance_name,
                                                                             tenant_name=tenant_name,
                                                                             old_instance_name=inst_name)
                        tenant_so, seq_no = tenanat_list.check_sale_order(instance_name=instance_name,
                                                                          sequence_no=seq_number, tenant_name=tenant,
                                                                          old_instance_name=inst_name)
                        rec.instance_name = tenant_so

            if automated and based_on == 'tax_number':
                for rec in self:
                    if rec.partner_id:
                        if not rec.partner_id.vat:
                            raise UserError(_("Customer %s doesn't have any Tax Number!", rec.parner_id.name))
                        vat_number = rec.partner_id.vat
                        # partner = rec.partner_id
                        inst_name = vat_number.replace(' ', "")
                        tenanat_list = request.env["tenant.database.list"].sudo()
                        tenant_name, sequence_number = tenanat_list.check_sequence_number(instance_name=inst_name,
                                                                                          sequence_no=0,
                                                                                          old_instance_name=inst_name)

                        tenant, seq_number = tenanat_list.check_phone_number(sequence_no=sequence_number,
                                                                             instance_name=inst_name,
                                                                             tenant_name=tenant_name,
                                                                             old_instance_name=inst_name)

                        tenant_so, seq_no = tenanat_list.check_sale_order(instance_name=inst_name,
                                                                          sequence_no=seq_number,
                                                                          tenant_name=tenant,
                                                                          old_instance_name=inst_name)
                        rec.instance_name = tenant_so
        else:
            self.instance_name = False
            # tenanat_list = request.env["tenant.database.list"].sudo().search([('name', '=', str(rec.partner_id.vat))])
            # if not tenanat_list:
            #     rec.instance_name = str(rec.partner_id.vat)
            # else:
            #     rec.instance_name =rec.partner_id.vat +'_'+ str(rec.partner_id.seq_no)
            #     tenanat_list = request.env["tenant.database.list"].sudo().search(
            #         [('name', '=', str(rec.instance_name))])
            #     tenant_name = tenanat_list.check_sequence_number(order=rec, partner=rec.partner_id, instance_name=inst_name,
            #                       sequence_no=1,old_instance_name=inst_name)
            #     rec.instance_name = str(rec.partner_id.vat) + '_' + str(rec.partner_id.seq_no)

    @api.onchange('saas_order')
    def _onchange_lang_opt(self):
        for rec in self:
            language_id = self.env['ir.config_parameter'].sudo().get_param('billing_type_extension.language_id')
            if language_id:
                rec.tenant_language = int(language_id)
            billing = self.env['ir.config_parameter'].sudo().search([('key', '=', 'billing')]).value
            if billing:
                rec.billing = billing


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('qty_invoiced', 'qty_delivered', 'product_uom_qty', 'order_id.state')
    def _get_to_invoice_qty(self):
        """
        Compute the quantity to invoice. If the invoice policy is order, the quantity to invoice is
        calculated from the ordered quantity. Otherwise, the quantity delivered is used.
        """
        for line in self:
            print("========fddf====================", line.order_id.state)
            if line.order_id.state in ['sale', 'done']:
                if line.product_id.invoice_policy == 'order':
                    line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
                else:
                    line.qty_to_invoice = line.qty_delivered - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

    @api.depends('state', 'product_id', 'untaxed_amount_invoiced', 'qty_delivered', 'product_uom_qty', 'price_unit')
    def _compute_untaxed_amount_to_invoice(self):

        """ Total of remaining amount to invoice on the sale order line (taxes excl.) as
                total_sol - amount already invoiced
            where Total_sol depends on the invoice policy of the product.

            Note: Draft invoice are ignored on purpose, the 'to invoice' amount should
            come only from the SO lines.
        """
        for line in self:
            print("=fgfgfdgfgfdgjkfglfdgf========================", line.state)
            amount_to_invoice = 0.0
            if line.state in ['sale', 'done']:
                # Note: do not use. price_subtotal field as it returns zero when the ordered quantity is
                # zero. It causes problem for expense line (e.i.: ordered qty = 0, deli qty = 4,
                # price_unit = 20 ; subtotal is zero), but when you can invoice the line, you see an
                # amount and not zero. Since we compute untaxed amount, we can use directly the price
                # reduce (to include discount) without using `compute_all()` method on taxes.
                price_subtotal = 0.0
                price_reduce = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                if line.product_id.invoice_policy == 'delivery':

                    price_subtotal = price_reduce * line.qty_delivered
                else:
                    price_subtotal = price_reduce * line.product_uom_qty

                amount_to_invoice = price_subtotal - line.untaxed_amount_invoiced
            line.untaxed_amount_to_invoice = amount_to_invoice * line.month

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        _logger.info("_compute_amount-------->>>>>....")

        """
        Compute the amounts of the SO line.Added for odoo 15
        """
        # super(sale_order_line, self)._compute_amount()
        config_path = request.env['ir.config_parameter'].sudo()
        tenant = self.env['tenant.database.list'].sudo().search([('name', '=', self.order_id.instance_topup_list.name)])
        agreement = self.env['sale.recurring.orders.agreement'].sudo().search(
            [('instance_name', '=', self.order_id.instance_topup_list.name)])

        date = datetime.datetime.now().date()
        for line in self:
            normal = True
            quantity = line.product_uom_qty
            users = line.order_id.no_of_users
            month = 1

            """This is written to calculate add more user price  while creating the instance 
                        from the portal for user+plan price"""
            # code start --->>>
            config_user_product = config_path.search(
                [('key', '=', 'user_product')]).value
            config_product = request.env['product.product'].sudo().search([('id', '=', int(config_user_product))])

            plan_users = int(config_path.search([('key', '=', 'plan_users')]).value or 1)
            if line.product_id == config_product and line.order_id.billing == 'user_plan_price' and line.order_id.instance_topup_list and not line.order_id.saas_order:
                _logger.info("line.product_id == config_product and line.order_id.billing == 'user_plan_price'")

                if users > plan_users:
                    _logger.info('Adding manage user line in the SO for user+plan price')
                    price = line.product_template_id.list_price
                    if line.order_id.invoice_term_id.name == "Yearly":
                        month = 12
                    if line.order_id.invoice_term_id.name == "Monthly":
                        month = 1

                    users = users - plan_users
                    extra_price = config_product.list_price
                    price = extra_price * month
                    taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                                    product=line.product_id,
                                                    partner=line.order_id.partner_shipping_id, months=month)
                    line.update({
                        'price_tax': taxes['total_included'] - taxes['total_excluded'],
                        'price_subtotal': taxes['total_excluded'],
                        'price_unit': price
                    })
                else:
                    _logger.info("if users < plan_users")
                    total_amount = line.product_template_id.list_price

                    # print('\n\ntotal_amount : ', total_amount)
                    remain_days = (tenant.exp_date - date).days
                    total_days = 0
                    if agreement.invoice_term_id.name == 'Monthly':
                        total_days = 30
                    elif agreement.invoice_term_id.name == 'Yearly':
                        total_days = 365
                        total_amount = total_amount * 12

                    one_user_price_for_one_day = total_amount / total_days

                    # print('&&&&&&&&&&&&&&&&&&&& : {} {} {} {}'.format(total_amount, total_days, one_user_price_for_one_day, remain_days))

                    extra_users_price_for_remain_day = one_user_price_for_one_day * remain_days

                    # Update Product MAster price
                    # product.lst_price = extra_users_price_for_remain_day
                    # product.standard_price = extra_users_price_for_remain_day
                    # order.saas_order = False
                    # ----------------------------------------------------
                    _logger.info("Entered the else caseeee 22222222")
                    price = extra_users_price_for_remain_day
                    taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                                    product=line.product_id,
                                                    partner=line.order_id.partner_shipping_id, months=month)
                    line.update({
                        'price_tax': taxes['total_included'] - taxes['total_excluded'],
                        'price_subtotal': taxes['total_excluded'],
                        'price_unit': extra_users_price_for_remain_day
                    })
            if line.product_id == config_product and line.order_id.billing == 'user_plan_price' and not line.order_id.instance_topup_list:
                _logger.info(
                    "line.product_id == config_product and line.order_id.billing == 'user_plan_price' and not line.order_id.instance_topup_list")
                duration = 1
                if line.order_id.invoice_term_id.name == 'Yearly':
                    duration = 12
                price = line.product_id.lst_price * duration
                taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                                product=line.product_id,
                                                partner=line.order_id.partner_shipping_id, months=duration)
                line.update({
                    'price_tax': taxes['total_included'] - taxes['total_excluded'],
                    'price_subtotal': taxes['total_excluded'],
                    'price_unit': price
                })


            elif line.product_template_id.is_saas:
                _logger.info("-------line.product_template_id.is_saas--------")
                if line.order_id.invoice_term_id and (line.product_id.is_saas or line.is_reward_line):
                    term = line.order_id.invoice_term_id
                    if term.type == 'from_first_date':
                        month = 1
                    elif term.type == 'quarter':
                        month = 3
                    elif term.type == 'half_year':
                        month = 6
                    elif term.type == 'year':
                        month = 12

                # print('Discount : {} '.format((1 - (line.discount or 0.0) / 100.0)))
                # discount = line.price_unit * (1 - (line.discount or 0.0) / 100.0)

                price = line.product_template_id.list_price
                config_user_product = config_path.search(
                    [('key', '=', 'user_product')]).value
                config_product = request.env['product.product'].sudo().search([('id', '=', int(config_user_product))])

                if line.order_id.billing == 'user_plan_price':
                    plan_users = int(config_path.search([('key', '=', 'plan_users')]).value or 1)
                    # print("priceeeeeeeeeeeee:", config_product.list_price)
                    # print("plan users:", plan_users,"users:",users,'Months : ', month)
                    # extra_users = 1

                    print(price, 'price')
                    print(month, "month")
                    price = price * month

                elif line.order_id.billing == 'normal' and line.order_id.invoice_term_id.name == "Yearly":
                    _logger.info("line.order_id.billing == 'normal' and line.order_id.invoice_term_id.name == 'Yearly'")
                    price = price * users * month


                elif line.order_id.billing == 'normal' and line.order_id.invoice_term_id.name == "Monthly":
                    price = price * line.order_id.no_of_users
                    print('Price 2222: {} {} {}'.format(price, users, month))

                if normal and line.order_id.saas_order and users and month:
                    if line.product_id.id == config_product.id:
                        price = price * users * month
                # print("line.discount--------------->>>>>>>>>>",line.discount)
                taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                                product=line.product_id,
                                                partner=line.order_id.partner_shipping_id, months=month)

                discount = taxes['total_excluded'] - (price * (1 - (line.discount or 0.0) / 100.0))

                # subtotal_amount =  taxes['total_excluded']
                line.update({
                    'price_tax': taxes['total_included'] - taxes['total_excluded'],
                    'price_total': taxes['total_included'],
                    'price_subtotal': taxes['total_excluded'] - discount,
                    'price_unit': taxes['total_excluded']
                })

                if self.env.context.get('import_file', False) and not self.env.user.user_has_groups(
                        'account.group_account_manager'):
                    line.tax_id.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_id.id])
            else:
                _logger.info("-------line.product_template_id.is NOT saas--------")
                field_keys = []
                reward_line = False
                for lines in line._fields.keys():
                    field_keys.append(lines)
                if 'is_reward_line' in field_keys:
                    reward_line = True
                    # if not line.is_reward_line:
                if line.order_id.billing == 'user_plan_price' and not reward_line:
                    _logger.info("Not Reward Line")
                    db_size_product = False
                    if line.order_id.db_space == True:
                        db_size_product = config_path.search(
                            [('key', '=', 'db_size_usage_product')]).value
                    elif line.order_id.filestore_space == True:
                        db_size_product = config_path.search(
                            [('key', '=', 'filestore_size_usage_product')]).value
                    if db_size_product:
                        db_product = self.env['product.product'].sudo().search([('id', '=', int(db_size_product))])
                        extra_price = db_product.list_price
                        taxes = line.tax_id.compute_all(extra_price, line.order_id.currency_id, line.product_uom_qty,
                                                        product=line.product_id,
                                                        partner=line.order_id.partner_shipping_id, months=month)
                        line.update({
                            'price_tax': taxes['total_included'] - taxes['total_excluded'],
                            'price_total': taxes['total_included'],
                            'price_subtotal': taxes['total_excluded'],
                            'price_unit': extra_price
                        })
                    else:
                        plan_users = int(config_path.search([('key', '=', 'plan_users')]).value or 1)
                        # print("priceeeeeeeeeeeee:", config_product.list_price)
                        # print("plan users:", plan_users,"users:",users,'Months : ', month)
                        extra_users = 1
                        normal = False
                        extra_price = line.price_unit
                        if users > plan_users:
                            users = users - plan_users
                            extra_price = config_product.list_price
                            # price = config_product.list_price
                            # price = extra_price * extra_users
                            # price = price * month
                            # print("Price :", price, "extra price :", extra_price, "extra users :", extra_users)

                        taxes = line.tax_id.compute_all(extra_price, line.order_id.currency_id, line.product_uom_qty,
                                                        product=line.product_id,
                                                        partner=line.order_id.partner_shipping_id, months=month)
                        line.update({
                            'price_tax': taxes['total_included'] - taxes['total_excluded'],
                            'price_total': taxes['total_included'],
                            'price_subtotal': taxes['total_excluded'],
                            'price_unit': extra_price
                        })
                else:
                    _logger.info("\n Reward Line Present\n")
                    field_keys = []
                    reward_line = False
                    for lines in line._fields.keys():
                        field_keys.append(lines)
                    if 'is_reward_line' in field_keys:
                        reward_line = True
                    # if not line.is_reward_line:
                    if line.order_id.billing == 'user_plan_price' and reward_line and not line.is_reward_line and not line.order_id.instance_topup_list:
                        _logger.info("line.order_id.billing == 'user_plan_price' and not reward_line")
                        db_size_product = False
                        term = 1
                        if line.order_id.invoice_term_id.name == "Yearly":
                            term = 12

                        if line.order_id.db_space == True:
                            db_size_product = config_path.search(
                                [('key', '=', 'db_size_usage_product')]).value
                        elif line.order_id.filestore_space == True:
                            db_size_product = config_path.search(
                                [('key', '=', 'filestore_size_usage_product')]).value

                        _logger.info("db_size_product------------->>{}".format(db_size_product))
                        if db_size_product:
                            extra_price = 0.00
                            db_product = self.env['product.product'].sudo().search([('id', '=', int(db_size_product))])
                            extra_price = db_product.list_price * term
                            taxes = line.tax_id.compute_all(extra_price, line.order_id.currency_id,
                                                            line.product_uom_qty,
                                                            product=line.product_id,
                                                            partner=line.order_id.partner_shipping_id, months=term)
                            line.update({
                                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                                'price_total': taxes['total_included'],
                                'price_subtotal': taxes['total_excluded'],
                                'price_unit': extra_price
                            })
                        else:
                            _logger.info("Manage user product")
                            plan_users = int(config_path.search([('key', '=', 'plan_users')]).value or 1)
                            # print("priceeeeeeeeeeeee:", config_product.list_price)
                            # print("plan users:", plan_users,"users:",users,'Months : ', month)
                            extra_users = 1
                            normal = False
                            extra_price = line.price_unit
                            if users > plan_users:
                                users = users - plan_users
                                extra_price = config_product.list_price
                                # price = config_product.list_price
                                # price = extra_price * extra_users
                                # price = price * month
                                # print("Price :", price, "extra price :", extra_price, "extra users :", extra_users)
                            taxes = line.tax_id.compute_all(extra_price, line.order_id.currency_id,
                                                            line.product_uom_qty,
                                                            product=line.product_id,
                                                            partner=line.order_id.partner_shipping_id, months=month)
                            _logger.info("Manage User---->>:{}".format(taxes))
                            line.update({
                                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                                'price_total': taxes['total_included'],
                                'price_subtotal': taxes['total_excluded'],
                                'price_unit': taxes['total_excluded']
                            })
                    if line.order_id.billing == 'user_plan_price' and reward_line and not line.is_reward_line and line.order_id.instance_topup_list:
                        db_size_product = False
                        term = 1
                        if line.order_id.invoice_term_id.name == "Yearly":
                            term = 12

                        if line.order_id.db_space == True:
                            db_size_product = config_path.search(
                                [('key', '=', 'db_size_usage_product')]).value
                        elif line.order_id.filestore_space == True:
                            db_size_product = config_path.search(
                                [('key', '=', 'filestore_size_usage_product')]).value

                        _logger.info("db_size_product------------->>{}".format(db_size_product))
                        if db_size_product:
                            extra_price = 0.00
                            db_product = self.env['product.product'].sudo().search([('id', '=', int(db_size_product))])
                            extra_price = db_product.list_price * term
                            taxes = line.tax_id.compute_all(extra_price, line.order_id.currency_id,
                                                            line.product_uom_qty,
                                                            product=line.product_id,
                                                            partner=line.order_id.partner_shipping_id, months=term)
                            line.update({
                                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                                'price_total': taxes['total_included'],
                                'price_subtotal': taxes['total_excluded'],
                                'price_unit': extra_price
                            })

                    # start

                    if line.order_id.billing == 'normal' and reward_line and not line.is_reward_line:
                        _logger.info("line.order_id.billing == 'normal' and not reward_line")
                        db_size_product = False
                        term = 1
                        if line.order_id.invoice_term_id.name == "Yearly":
                            term = 12

                        if line.order_id.db_space == True:
                            db_size_product = config_path.search(
                                [('key', '=', 'db_size_usage_product')]).value
                        elif line.order_id.filestore_space == True:
                            db_size_product = config_path.search(
                                [('key', '=', 'filestore_size_usage_product')]).value

                        _logger.info("db_size_product------------->>".format(db_size_product))
                        if db_size_product:
                            extra_price = 0.00
                            db_product = self.env['product.product'].sudo().search([('id', '=', int(db_size_product))])
                            tenant = self.env['tenant.database.list'].sudo().search(
                                [('id', '=', line.order_id.instance_topup_list.id)])
                            users = tenant.sale_order_ref.no_of_users
                            extra_price = db_product.list_price * term * users
                            taxes = line.tax_id.compute_all(extra_price, line.order_id.currency_id,
                                                            line.product_uom_qty,
                                                            product=line.product_id,
                                                            partner=line.order_id.partner_shipping_id, months=term)
                            line.update({
                                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                                'price_total': taxes['total_included'],
                                'price_subtotal': taxes['total_excluded'],
                                'price_unit': extra_price
                            })
                        else:
                            total_app_price = 0.00
                            lines = agreement.agreement_line
                            saas_product = lines.filtered(lambda x: x.product_id.is_saas == True)
                            user = self.env.user

                            for rec in saas_product:
                                price_list = user.partner_id.property_product_pricelist
                                if price_list:
                                    record = price_list._get_applicable_rules(rec.product_id, date)
                                    # suitable_rule = False
                                    if record:
                                        for items in record:
                                            if items._is_applicable_for(rec.product_id, 1.0):
                                                suitable_rule = items
                                                break
                                            if suitable_rule:
                                                price = suitable_rule._compute_price(product=rec.product_id,
                                                                                     quantity=1.0,
                                                                                     uom=rec.product_id.uom_id,
                                                                                     date=date)
                                                total_app_price += price
                                    else:
                                        price = rec.price
                                        total_app_price += price

                            remain_days = (tenant.exp_date - date).days
                            total_days = 0
                            if agreement.invoice_term_id.name == 'Monthly':
                                total_days = 30
                                total_app_price = total_app_price

                            elif agreement.invoice_term_id.name == 'Yearly':
                                total_days = 365
                                total_app_price = total_app_price
                            per_day_price = total_app_price / total_days
                            extra_users_price_for_remain_day = per_day_price * remain_days
                            _logger.info("Manage user product")
                            plan_users = int(config_path.search([('key', '=', 'plan_users')]).value or 1)
                            taxes = line.tax_id.compute_all(extra_users_price_for_remain_day, line.order_id.currency_id,
                                                            product=line.product_id,
                                                            partner=line.order_id.partner_shipping_id, months=month)
                            _logger.info("Manage User---->>".format(taxes))

                            line.update({
                                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                                'price_total': taxes['total_included'],
                                'price_subtotal': taxes['total_excluded'],
                                'price_unit': taxes['total_excluded']
                            })
                    # end
                    else:
                        for line in self:
                            tax_results = self.env['account.tax']._compute_taxes(
                                [line._convert_to_tax_base_line_dict()])
                            totals = list(tax_results['totals'].values())[0]
                            amount_untaxed = totals['amount_untaxed']
                            amount_tax = totals['amount_tax']

                            line.update({
                                'price_subtotal': amount_untaxed,
                                'price_tax': amount_tax,
                                'price_total': amount_untaxed + amount_tax,
                            })

    def _get_invoice_term_months(self):
        res = {}
        for sol in self:
            if sol.order_id.saas_order:
                res[sol.id] = 1
                instance_name = sol.order_id.instance_name
                if instance_name:
                    # ===============================================================
                    # On "Confirm" click
                    # For new and top up both orders Charge for all months in subscription use this code
                    # ======================= Start ========================================
                    type = sol.order_id.invoice_term_id.type
                    if type == 'from_first_date': sol.month = 1
                    if type == 'quarter': sol.month = 3
                    if type == 'half_year': sol.month = 6
                    if type == 'year': sol.month = 12
                    if type is False or None: sol.month = 1
                else:
                    self.month = 1
                # =================== End ================================================
            else:
                self.month = 1
        return res

    @api.model_create_multi
    # @api.returns('self', lambda value:value.id)
    def create(self, vals):
        for val in vals:
            if 'display_type' in val and val['display_type'] == False:
                product_id = self.env['product.product'].search([('id', '=', val['product_id'])])
                if 'product_uos_qty' in val:
                    val['product_uom_qty'] = val['product_uos_qty']
                if 'price_unit' in val:
                    val.update({'name': product_id.name})
                    # val.update({'price_subtotal':'price_unit'})
            # return models.Model.create(self, vals)
            res = super(sale_order_line, self).create(vals)
            return res

    def write(self, vals):
        print("\n\nOrder Lines vals :", vals)
        if 'price_unit' in vals:
            print(111111111, vals)
        print("============models.Model============",models.Model)
        return models.Model.write(self, vals)

    # 'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account')),
    month = fields.Integer(compute='_get_invoice_term_months', string='Invoice Term', default=1)

    def _prepare_invoice_line(self, **optional_values):
        res = super(sale_order_line, self)._prepare_invoice_line(**optional_values)
        res.update({'month': self.month,
                    'no_of_users': self.order_id.no_of_users,
                    'billing': self.order_id.billing})
        return res

    # def calculate_price_for_invoice_with_pricelist(self, line, month):
    #     product = line.product_id.with_context(
    #         partner=self.order_id.partner_id,
    #         quantity=line.product_uom_qty * month,
    #         date=self.order_id.date_order,
    #         pricelist=self.order_id.pricelist_id.id,
    #         uom=line.product_uom.id
    #     )
    #     price_unit = self.env['account.tax']._fix_tax_included_price_company(
    #         line._get_display_price(product), line.product_id.taxes_id, line.tax_id, line.company_id)
    #
    #     return price_unit


class AccountTax(models.Model):
    _inherit = 'account.tax'
    """Inherited to override tax calculation methode"""

    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None, is_refund=False,
                    handle_price_include=True, include_caba_tags=False, fixed_multiplicator=1, users=1.0, months=1.0):
        _logger.info(" -------------------Entering compute_all--------------------------")

        if not self:
            company = self.env.company
        else:
            company = self[0].company_id

        taxes, groups_map = self.flatten_taxes_hierarchy(create_map=True)
        base_excluded_flag = False  # price_include=False && include_base_amount=True
        included_flag = False  # price_include=True
        for tax in taxes:
            if tax.price_include:
                included_flag = True
            elif tax.include_base_amount:
                base_excluded_flag = True
            if base_excluded_flag and included_flag:
                raise UserError(_(
                    'Unable to mix any taxes being price included with taxes affecting the base amount but not included in price.'))

        if not currency:
            currency = company.currency_id
        prec = currency.rounding

        round_tax = False if company.tax_calculation_rounding_method == 'round_globally' else True
        if 'round' in self.env.context:
            round_tax = bool(self.env.context['round'])

        if not round_tax:
            prec *= 1e-5

        def recompute_base(base_amount, fixed_amount, percent_amount, division_amount):

            return (base_amount - fixed_amount) / (1.0 + percent_amount / 100.0) * (100 - division_amount) / 100

        base = currency.round(price_unit * quantity * users)

        print("\nusersssssssssssssss\n", users)

        sign = 1
        if currency.is_zero(base):
            sign = self._context.get('force_sign', 1)
        elif base < 0:
            sign = -1
        if base < 0:
            base = -base

        total_included_checkpoints = {}
        i = len(taxes) - 1
        store_included_tax_total = True
        # Keep track of the accumulated included fixed/percent amount.
        incl_fixed_amount = incl_percent_amount = incl_division_amount = 0
        # Store the tax amounts we compute while searching for the total_excluded
        cached_tax_amounts = {}
        if handle_price_include:
            for tax in reversed(taxes):
                tax_repartition_lines = (
                        is_refund
                        and tax.refund_repartition_line_ids
                        or tax.invoice_repartition_line_ids
                ).filtered(lambda x: x.repartition_type == "tax")
                sum_repartition_factor = sum(tax_repartition_lines.mapped("factor"))

                if tax.include_base_amount:
                    base = recompute_base(base, incl_fixed_amount, incl_percent_amount, incl_division_amount)
                    incl_fixed_amount = incl_percent_amount = incl_division_amount = 0
                    store_included_tax_total = True
                if tax.price_include or self._context.get('force_price_include'):
                    if tax.amount_type == 'percent':
                        incl_percent_amount += tax.amount * sum_repartition_factor
                    elif tax.amount_type == 'division':
                        incl_division_amount += tax.amount * sum_repartition_factor
                    elif tax.amount_type == 'fixed':
                        incl_fixed_amount += quantity * users * tax.amount * sum_repartition_factor
                    else:
                        # tax.amount_type == other (python)
                        tax_amount = tax._compute_amount(base, sign * price_unit, quantity, product,
                                                         partner) * sum_repartition_factor
                        incl_fixed_amount += tax_amount
                        # Avoid unecessary re-computation
                        cached_tax_amounts[i] = tax_amount
                    # In case of a zero tax, do not store the base amount since the tax amount will
                    # be zero anyway. Group and Python taxes have an amount of zero, so do not take
                    # them into account.
                    if store_included_tax_total and (
                            tax.amount or tax.amount_type not in ("percent", "division", "fixed")
                    ):
                        total_included_checkpoints[i] = base
                        store_included_tax_total = False
                i -= 1

        total_excluded = currency.round(
            recompute_base(base, incl_fixed_amount, incl_percent_amount, incl_division_amount))

        base = total_included = total_void = total_excluded
        taxes_vals = []
        i = 0
        cumulated_tax_included_amount = 0
        for tax in taxes:
            tax_repartition_lines = (
                    is_refund and tax.refund_repartition_line_ids or tax.invoice_repartition_line_ids).filtered(
                lambda x: x.repartition_type == 'tax')
            sum_repartition_factor = sum(tax_repartition_lines.mapped('factor'))
            price_include = self._context.get('force_price_include', tax.price_include)

            # compute the tax_amount
            if price_include and total_included_checkpoints.get(i):
                # We know the total to reach for that tax, so we make a substraction to avoid any rounding issues
                tax_amount = total_included_checkpoints[i] - (base + cumulated_tax_included_amount)
                cumulated_tax_included_amount = 0
            else:
                tax_amount = tax.with_context(force_price_include=False)._compute_amount(
                    base, sign * price_unit, quantity, product, partner)

            # Round the tax_amount multiplied by the computed repartition lines factor.
            tax_amount = round(tax_amount, precision_rounding=prec)
            factorized_tax_amount = round(tax_amount * sum_repartition_factor, precision_rounding=prec)

            if price_include and not total_included_checkpoints.get(i):
                cumulated_tax_included_amount += factorized_tax_amount

            # If the tax affects the base of subsequent taxes, its tax move lines must
            # receive the base tags and tag_ids of these taxes, so that the tax report computes
            # the right total
            subsequent_taxes = self.env['account.tax']
            subsequent_tags = self.env['account.account.tag']
            if tax.include_base_amount:
                subsequent_taxes = taxes[i + 1:]
                subsequent_tags = subsequent_taxes.get_tax_tags(is_refund, 'base')

            # Compute the tax line amounts by multiplying each factor with the tax amount.
            # Then, spread the tax rounding to ensure the consistency of each line independently with the factorized
            # amount. E.g:
            #
            # Suppose a tax having 4 x 50% repartition line applied on a tax amount of 0.03 with 2 decimal places.
            # The factorized_tax_amount will be 0.06 (200% x 0.03). However, each line taken independently will compute
            # 50% * 0.03 = 0.01 with rounding. It means there is 0.06 - 0.04 = 0.02 as total_rounding_error to dispatch
            # in lines as 2 x 0.01.
            repartition_line_amounts = [round(tax_amount * line.factor, precision_rounding=prec) for line in
                                        tax_repartition_lines]
            total_rounding_error = round(factorized_tax_amount - sum(repartition_line_amounts), precision_rounding=prec)
            nber_rounding_steps = int(abs(total_rounding_error / currency.rounding))
            rounding_error = round(nber_rounding_steps and total_rounding_error / nber_rounding_steps or 0.0,
                                   precision_rounding=prec)
            for repartition_line, line_amount in zip(tax_repartition_lines, repartition_line_amounts):

                if nber_rounding_steps:
                    line_amount += rounding_error
                    nber_rounding_steps -= 1

                taxes_vals.append({
                    'id': tax.id,
                    'name': partner and tax.with_context(lang=partner.lang).name or tax.name,
                    'amount': sign * line_amount,
                    'base': round(sign * base, precision_rounding=prec),
                    'sequence': tax.sequence,
                    'account_id': tax.cash_basis_transition_account_id.id if tax.tax_exigibility == 'on_payment' else repartition_line.account_id.id,
                    'analytic': tax.analytic,
                    'use_in_tax_closing': repartition_line.use_in_tax_closing,
                    'price_include': price_include,
                    'tax_exigibility': tax.tax_exigibility,
                    'tax_repartition_line_id': repartition_line.id,
                    'group': groups_map.get(tax),
                    'tag_ids': (repartition_line.tag_ids + subsequent_tags).ids,
                    'tax_ids': subsequent_taxes.ids,
                })

                if not repartition_line.account_id:
                    total_void += line_amount

            # Affect subsequent taxes
            if tax.include_base_amount:
                base += factorized_tax_amount

            total_included += factorized_tax_amount
            i += 1
        return {
            'base_tags': taxes.mapped(
                is_refund and 'refund_repartition_line_ids' or 'invoice_repartition_line_ids').filtered(
                lambda x: x.repartition_type == 'base').mapped('tag_ids').ids,
            'taxes': taxes_vals,
            'total_excluded': sign * total_excluded,
            'total_included': sign * currency.round(total_included),
            'total_void': sign * currency.round(total_void),
        }

