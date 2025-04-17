# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################
from pdb import set_trace
from odoo.addons.mobikul.tool.service import WebServices
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.mobikul.tool.help import _displayWithCurrency, _get_image_url, _get_ar_url,_changePricelist, _get_product_domain, remove_htmltags, AQUIRER_REF_CODES, STATUS_MAPPING, _get_next_reference,EMPTY_ADDRESS, _easy_date
from odoo import _,fields
from odoo.http import request, route
from odoo.fields import Datetime, Date, Selection
from odoo.exceptions import UserError, ValidationError
import logging
from ast import literal_eval
import uuid
import json
import base64
_logger = logging.getLogger(__name__)
import re

ADMIN_USER = [1,2]

ANONYMIZED_DETAILS = { "user": {
                            "user_fields":["name"],
                            "user_social_login_fields":["oauth_uid","oauth_access_token"]
                            },
                       "partner":{
                           "partner_fields":["name","street","street2","city","zip","company_name","email"],
                            "partner_related_fields":["state_id","country_id","last_mobikul_so_id"]
                             }
                     }

class MobikulApi(WebServices):

    @route('/mobikul/splashPageData', csrf=False, type='http', auth="none", methods=['POST'])
    def getSplashPageData(self, **kwargs):
        response = self._authenticate(False, **kwargs)
        if response.get('success'):
            Mobikul = response.get("context").get("mobikul_obj")
            if 'login' in self._lcred:
                result = Mobikul.authenticate(self._lcred, True, self._sLogin, context=response['context'])
                response.update(result)
                if response.get('addons', {}).get('wishlist') and response.get('customerId'):
                    response['wishlist'] = self._website_Wishlist(response.get('customerId'))

            result = Mobikul.getDefaultData()
            response.update(result)
            response['sortData'] = [
                ("Price: High to Low", "price desc"),
                ("Price: Low to High", "price asc"),
                ("Discounts", "id asc"),
                ("Popularity", "id asc"),
                ("Newest First", "id desc"),
            ]
            response['message'] = "Splash Data."
            response.update(self._languageData(Mobikul))
            response.update(self._pricelistData(Mobikul))
            if response.get('addons', {}).get('review'):
                response['RatingStatus'] = [
                    ("1", _("Poor")),
                    ("2", _("Ok")),
                    ("3", _("Good")),
                    ("4", _("Very Good")),
                    ("5", _("Excellent")),
                ]
        return self._response('splashPageData', response)

    @route('/mobikul/customer/login', csrf=False, type='http', auth="none", methods=['POST'])
    def login(self, **kwargs):
        kwargs['detailed'] = True
        response = self._authenticate(True, **kwargs)
        user = response.get('context').get('user')
        if response.get('context').get('tz'):
            user.tz = response.get('context').get('tz')
        self._tokenUpdate(customer_id=response.get('customerId'))
        if response.get('success'):
            token = request.httprequest.headers.get("fcmToken") or self._mData.get("fcmToken") or ""
            self._pushNotification(token,condition = 'login',
                                       customer_id = response.get('customerId'))
        return self._response('login', response)

    @route('/mobikul/customer/signOut', csrf=False, type='http', auth="none", methods=['POST'])
    def signOut(self, **kwargs):
        response = self._authenticate(False, **kwargs)
        if response.get('success'):
            response['message'] = "Have a Good Day !!!"
            self._tokenUpdate()
        return self._response('signOut', response)

    @route('/mobikul/customer/signUp', csrf=False, type='http', auth="public",website=True, methods=['POST'])
    def signUp(self, **kwargs):
        response = self._authenticate(False, **kwargs)
        if response.get('success'):
            createNotification = False
            Mobikul = response.get("context").get("mobikul_obj")
            # response.update(self._languageData(Mobikul))
            result = Mobikul.signUp(self._mData)
            response.update(result)
            if response['success'] and response.get('addons', {}).get('email_verification'):
                if not self._mData.get('authUserId', False):
                    response["message"] = _(
                        "An email has been sent to your email address. Please verify it.")
                    response['createNotification'] = True
            if response['success']:
                context = response.get("context")
                login = {}
                if self._mData.get('authUserId', False):
                    cred = {'authUserId': self._mData.get(
                        'authUserId', ""), 'authProvider': self._mData.get('authProvider', "")}
                else:
                    cred = {'login': self._mData.get(
                        'login', ""), 'pwd': self._mData.get('password', "")}
                login = Mobikul.authenticate(cred, True, self._sLogin,
                                             context=context)
                user = login.get('context').get('user')
                if login.get('context').get('tz'):
                    user.tz = response.get('context').get('tz')
                if "context" in login:
                    del login['context']
                response.get('context').get('websiteObj').pricelist_id = response.get('context').get('pricelist').id
                response.update({"login": login, "cred": cred})
                homepage = Mobikul.homePage(self._mData, context)
                homepage.update(self._languageData(Mobikul))
                response.update({"homepage": homepage})
            self._tokenUpdate(customer_id=response.get('customerId'))
            if response.get("createNotification"):
                token = request.httprequest.headers.get("fcmToken") or self._mData.get("fcmToken") or ""
                self._pushNotification(token,
                                       customer_id=response.get('customerId'))
                response.pop("createNotification")
        return self._response('signUp', response)

    @route('/mobikul/customer/resetPassword', csrf=False, type='http', auth="public", methods=['POST'])
    def resetPassword(self, **kwargs):
        response = self._authenticate(False, **kwargs)
        if response.get('success'):
            Mobikul = request.env['mobikul'].sudo()
            result = Mobikul.resetPassword(self._mData.get('login', False))
            response.update(result)
        return self._response('resetPassword', response)

    @route('/mobikul/homepage', csrf=False, type='http', auth="public",website=True, methods=['POST'])
    def getHomepage(self, **kwargs):
        kwargs["sync_order"] = True
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            Mobikul = response.get("context").get("mobikul_obj")
            response.update(self._languageData(Mobikul))
            response.update(self._pricelistData(Mobikul))
            result = Mobikul.homePage(self._mData, response.get("context"), **kwargs)
            response.update(result)
            response['message'] = _("Homepage Data.")
            self._tokenUpdate(customer_id=response.get('customerId'))
            if response.get('addons', {}).get('wishlist') and response.get('customerId'):
                response['wishlist'] = self._website_Wishlist(response.get('customerId'))
        return self._response('homepage', response)

    @route('/mobikul/search', csrf=False, type='http', auth="public",website=True, methods=['POST'])
    def getSearchData(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            Mobikul = response.get("context").get("mobikul_obj")
            result = Mobikul.fetch_products(context=response.get("context"), **self._mData)
            response.update(result)
            response['message'] = "Search result."
            if response.get('addons', {}).get('wishlist') and response.get('customerId'):
                response['wishlist'] = self._website_Wishlist(response.get('customerId'))
        return self._response('search', response)

    @route(['/mobikul/sliderProducts/<int:slider_id>'], type='http', auth="public", csrf=False,website=True, methods=['GET', 'POST'])
    def getSliderProducts(self, slider_id, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('addons', {}).get('wishlist') and response.get('customerId'):
            response['wishlist'] = self._website_Wishlist(response.get('customerId'))
        if response.get('success'):
            PSlider = request.env['mobikul.product.slider'].search([('id', '=', slider_id)])
            if PSlider:
                context = response.get("context")
                context.update({
                    'limit': response.get('itemsPerPage', 5),
                    'offset': self._mData.get('offset', 0),
                    'order': self._mData.get('order', None),
                })
                response.update(PSlider.get_product_data(context))
                response['message'] = "Product slider ."
            else:
                response.update({'success': False, 'message': 'Product Slider not found !!!'})
        return self._response('sliderProducts', response)

    @route('/mobikul/template/<int:template_id>', csrf=False, type='http', auth="public", website=True, methods=['POST'])
    def getTemplateData(self, template_id, **kwargs):
        response = self._authenticate(True, **kwargs)
        local = response.get('context', {})
        if response.get('success'):
            addons = response.get('addons', {})
            wishlist = []
            if addons.get('wishlist') and response.get('customerId'):
                wishlist = self._website_Wishlist(response.get('customerId', 0))
            TemplateObj = request.env['product.template'].sudo()
            Template = TemplateObj.browse(template_id)
            if addons.get('website_sale_stock'):
                Template = Template.with_context(website_sale_stock_get_quantity=True)
            if Template:
                result = {
                    'templateId'	: Template.id,
                    'name'			: Template.name or "",
                    'attributes'	: [],
                    "images": [],
                    "message": "Template detail."
                }
                if addons.get('review'):
                    result.update({
                        'avg_rating': Template.avg_review(),
                        'total_review': len(Template.fetch_active_review(Template.id))
                    })
                if addons.get('odoo_marketplace'):
                    if Template.marketplace_seller_id and Template.marketplace_seller_id.website_published:
                        result.update({
                            'seller_info': {
                                'seller_profile_url'	: "/myTemplateseller/%s" % Template.marketplace_seller_id.id,
                                'marketplace_seller_id'	: Template.marketplace_seller_id.id,
                                'seller_name'			: Template.marketplace_seller_id.name,
                                'seller_profile_image'	: self.get_marketplace_image_url(self.base_url, 'res.partner', Template.marketplace_seller_id.id, 'profile_image', Template.marketplace_seller_id.write_date),
                                'average_rating'		: Template.marketplace_seller_id.avg_review(),
                                'total_reviews'			: len(Template.marketplace_seller_id.seller_review_ids.filtered(lambda r: (r.active == True and r.state == "pub"))),
                                'message'				: str(Template.marketplace_seller_id.total_active_recommendation()[1])+" positive feedback (%s ratings)" % Template.marketplace_seller_id.avg_review()
                            }
                        })
                    else:
                        result.update({
                            'seller_info': None
                        })
                prd_images = [_get_image_url(
                    self.base_url, 'product.image', im.id, 'image_1920', im.write_date) for im in Template.product_template_image_ids]
                for ali in Template.attribute_line_ids:
                    temp = {
                        "name": ali.attribute_id.name or "",
                        "attributeId": ali.attribute_id.id,
                        "type": ali.attribute_id.display_type,
                        "newVariant": ali.attribute_id.create_variant,
                        "values": []
                    }
                    for v in ali.value_ids:
                        temp["values"].append({
                            "name": v.name or "",
                            "valueId": v.id,
                            "htmlCode": v.html_color or "",
                            "newVariant": ali.attribute_id.create_variant,
                        })
                    result['attributes'].append(temp)

                website = request.env['website'].get_current_website()
                comb_info = Template._get_combination_info(combination=False, product_id=False,add_qty=1,parent_combination=False, only_template=False)
                result.update({
                    'priceUnit'		: _displayWithCurrency(local.get('lang_obj'), comb_info['has_discounted_price'] and comb_info['list_price'] or comb_info['price'], local.get('currencySymbol'), local.get('currencyPosition')),
                    'priceReduce'	: comb_info['has_discounted_price'] and _displayWithCurrency(local.get('lang_obj'), comb_info['price'], local.get('currencySymbol'), local.get('currencyPosition')) or "",
                    'productId'		: Template.product_variant_id and Template.product_variant_id.id or '',
                    'productCount'	: Template.product_variant_count,
                    'description'	: Template.description_sale or "",
                    "alternativeProducts": [{
                        "templateId": product.id,
                        "name": product.name,
                        "image": _get_image_url(self.base_url, 'product.template', product.id, 'image_1024', product.write_date),
                    }
                        for product in Template.alternative_product_ids
                    ],
                    'ar_ios'     : _get_ar_url(self.base_url, 'product.template', Template.id, 'ar_image_ios',Template),
                    'ar_android'     : _get_ar_url(self.base_url, 'product.template', Template.id, 'ar_image_apk',Template),
                    'thumbNail'		: _get_image_url(self.base_url, 'product.template', Template.id, 'image_1920', Template.write_date),
                    'images'		: [_get_image_url(self.base_url, 'product.template', Template.id, 'image_1920', Template.write_date)] + prd_images,
                    'absoluteUrl': '%sshop/product/%s' % (self.base_url, slug(Template)),
                    "addedToWishlist": Template.product_variant_id.id in wishlist,
                    'variants'	: []
                })
                if addons.get('website_sale_stock'):
                    result.update(self.get_stock_info(comb_info, Template.product_variant_id and Template.product_variant_id, local))
                if Template.product_variant_count > 1:
                    for var in Template.product_variant_ids:
                        comb_info = Template._get_combination_info(combination=False, product_id=var.id,add_qty=1, parent_combination=False, only_template=False)   #$$$$
                        temp = {
                            "productId": var.id,
                            'images': [_get_image_url(self.base_url, 'product.product', var.id, 'image_1920', var.write_date)] + prd_images,
                            'ar_ios'     : _get_ar_url(self.base_url, 'product.product', var.id, 'ar_image_ios',var),
                            'ar_android'     : _get_ar_url(self.base_url, 'product.product', var.id, 'ar_image_apk',var),
                            'absoluteUrl': '%sshop/product/%s' % (self.base_url, slug(Template)),
                            'priceReduce': comb_info['has_discounted_price'] and _displayWithCurrency(local.get('lang_obj'), comb_info['price'], local.get('currencySymbol'), local.get('currencyPosition')) or "",
                            'priceUnit': _displayWithCurrency(local.get('lang_obj'), comb_info['has_discounted_price'] and comb_info['list_price'] or comb_info['price'], local.get('currencySymbol'), local.get('currencyPosition')),
                            "combinations": [],
                            "addedToWishlist": var.id in wishlist,
                        }
                        for ptavi in var.product_template_attribute_value_ids:
                            temp["combinations"].append({
                                "valueId": ptavi.product_attribute_value_id and ptavi.product_attribute_value_id.id,
                                "attributeId": ptavi.attribute_id and ptavi.attribute_id.id,
                            })
                        if addons.get('website_sale_stock'):
                            temp.update(self.get_stock_info(comb_info, var, local))
                        result['variants'].append(temp)
            else:
                result = {'success': False, 'message': 'Template not found !!!'}
            response.update(result)
        return self._response('template', response)

    @route('/mobikul/my/orders', csrf=False, type='http', auth="none", methods=['POST'])
    def getMyOrders(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            local = response.get('context', {})
            Partner = response.get("context").get('partner') if not local.get('is_guest') else False
            result = {}
            result['tcount'] = 0
            result['recentOrders'] = []
            if Partner:
                fields = ['name', 'create_date', 'state', 'amount_total', 'partner_shipping_id']
                SaleOrder = request.env['sale.order'].with_user(local['user']).sudo()

                domain = [
                    ('partner_id', '=', Partner.id),
                    ('state', 'not in', ('draft',))
                ]
                if self._mData.get('date_from', False) and self._mData.get('date_to', False):
                    domain += [('create_date', '>', self._mData.get('date_from')),
                               ('create_date', '<=', self._mData.get('date_to'))]

                result['tcount'] = SaleOrder.search_count(domain)
                orders = SaleOrder.search(domain, limit=self._mData.get('limit', response.get(
                    'itemsPerPage', 5)), offset=self._mData.get('offset', 0),  order="id desc")

                state_value = dict(SaleOrder.fields_get(["state"],['selection'])['state']["selection"])
                for order in orders:
                    order_date = request.env['ir.qweb.field.datetime'].sudo().value_to_html(order.date_order,{"tz_name":local.get('tz')})
                    ShippingAdd = order.sudo().partner_shipping_id[0]
                    temp = {
                        'id': order['id'],
                        'name': order['name'] or "",
                        'create_date': order_date or "",
                        'shipping_address': ShippingAdd and self.mobikul_display_address(ShippingAdd._display_address(), ShippingAdd.name) or "",
                        'shipAdd_url': ShippingAdd and '/mobikul/my/address/%s' % ShippingAdd.id or "",
                        'amount_total': _displayWithCurrency(local.get('lang_obj'), order['amount_total'], order.pricelist_id.currency_id.symbol,order.pricelist_id.currency_id.position),
                        'status': state_value[order['state']],
                        'canReOrder': order['state'] == 'sale',
                        'needCartMerge': True if Partner.last_mobikul_so_id else False,
                        'url': "/mobikul/my/order/%s" % order['id'],
                    }
                    result['recentOrders'].append(temp)
                    result['message'] = "Orders lists."
            else:
                result.update({'success': True, 'message': 'Guest User :No Orders found !!!'})
            response.update(result)
        return self._response('orders', response)

    @route('/mobikul/my/order/<int:order_id>', csrf=False, type='http', auth="none", methods=['POST'])
    def getMyOrder(self, order_id, **kwargs):
        response = self._authenticate(True, **kwargs)
        local = response.get('context',{})
        if response.get('success'):
            addons = response.get('addons', {})
            Partner = response.get("context").get('partner') if not local.get('is_guest') else False
            orderObj = request.env['sale.order'].sudo()
            Order = orderObj.search([("id","=",order_id)])
            state_value = dict(orderObj.fields_get(["state"],['selection'])['state']["selection"])
            if Order and not local.get('is_guest'):
                dateObj = request.env['ir.qweb.field.datetime'].sudo()
                o_time = dateObj.value_to_html(Order.date_order,{"tz_name":local.get('tz')})
                access_token =  str(uuid.uuid4())
                result = {
                    'id': Order.id or -1,
                    'name': Order.name or "",
                    "create_date": o_time,
                    'amount_total': _displayWithCurrency(local.get('lang_obj'), Order.amount_total, Order.pricelist_id.currency_id.symbol, Order.pricelist_id.currency_id.position),
                    'status': state_value[Order.state],
                    'canReOrder': Order.state == 'sale',
                    'needCartMerge': True if Partner.last_mobikul_so_id else False,
                    'amount_untaxed': _displayWithCurrency(local.get('lang_obj'), Order.amount_untaxed, Order.pricelist_id.currency_id.symbol, Order.pricelist_id.currency_id.position),
                    'amount_tax': _displayWithCurrency(local.get('lang_obj'), Order.amount_tax, Order.pricelist_id.currency_id.symbol, Order.pricelist_id.currency_id.position),
                    'shipping_address': self.mobikul_display_address(Order.partner_shipping_id._display_address(), Order.partner_shipping_id.name),
                    'shipAdd_url': '/mobikul/my/address/%s' % Order.partner_shipping_id.id,
                    'billing_address': self.mobikul_display_address(Order.partner_invoice_id._display_address(), Order.partner_invoice_id.name),
                    'delivery_latitude':Order.partner_id.partner_latitude and str(Order.partner_id.partner_latitude) or "",
                    'delivery_longitude':Order.partner_id.partner_longitude and str(Order.partner_id.partner_longitude) or "",
                    'isOrderInvoiced': True if Order.invoice_ids else False,
                }
                if Order.invoice_ids:
                    result['download_invoice'] = "%smobikul/invoices/%s?access_token=%s&report_type=pdf&download=true" % (self.base_url,Order.invoice_ids[-1].id,access_token)
                result['items'] = []

                for line in Order.order_line.sudo():
                    if response.get('addons', {}).get('delivery') and line.is_delivery:
                        shippingMethod = {
                            "tax": [tax.name for tax in line.tax_id],
                            "name": line.order_id.carrier_id.name,
                            "description": line.order_id.carrier_id.website_description or "",
                            "shippingId": line.order_id.carrier_id.id,
                            "total": _displayWithCurrency(local.get('lang_obj'), line.price_subtotal,
                                                          Order.pricelist_id.currency_id.symbol, Order.pricelist_id.currency_id.position),
                        }
                        result.update({"delivery": shippingMethod})
                    elif line.invoice_lines or line.name == "Down Payments":
                        pass
                    else:
                        temp = {
                            'name': line.name or "",
                            'product_name': line.product_id and line.product_id.display_name or "",
                            'qty': "%s %s" % (line.sudo().product_uom_qty, line.sudo().product_uom.name),
                            'price_unit': _displayWithCurrency(local.get('lang_obj'), line.price_unit,Order.pricelist_id.currency_id.symbol, Order.pricelist_id.currency_id.position),
                            'price_subtotal': _displayWithCurrency(local.get('lang_obj'), line.price_subtotal, Order.pricelist_id.currency_id.symbol, Order.pricelist_id.currency_id.position),
                            'price_tax': _displayWithCurrency(local.get('lang_obj'), line.price_tax, Order.pricelist_id.currency_id.symbol, Order.pricelist_id.currency_id.position),
                            'price_total': _displayWithCurrency(local.get('lang_obj'), line.price_total, Order.pricelist_id.currency_id.symbol, Order.pricelist_id.currency_id.position),
                            'discount': "%s" % (line.discount and "%s %%" % line.discount or ""),
                            'state': state_value[line.state],
                            'thumbNail'		: _get_image_url(self.base_url, 'product.product', line.product_id and line.product_id.id or "", 'image_1920', line.product_id and line.product_id.write_date),
                            "templateId": line.product_id and line.product_id.product_tmpl_id.id or "",
                        }
                        result['items'].append(temp)
                        result['message'] = "Order details."
                result['picking_details'] = []
                if addons.get('delivery_boy') and Order.state == 'sale' and Order.picking_ids:
                    for picking in Order.picking_ids:
                        warehouse_data = {
                            "address": picking.location_id.warehouse_id.partner_id.contact_address or '',
                            "lat": picking.location_id.warehouse_id.partner_id.partner_latitude and str(picking.location_id.warehouse_id.partner_id.partner_latitude) or '',
                            "long": picking.location_id.warehouse_id.partner_id.partner_longitude and str(picking.location_id.warehouse_id.partner_id.partner_longitude) or ''
                            }
                        picking_data = {
                            "deliveryBoyId":picking.delivery_boy_partner_id.id or 0,
                            "name" : picking.delivery_boy_picking_id.name or "",
                            "status":picking.delivery_boy_picking_id.picking_state or "",
                            "create_date":dateObj.value_to_html(picking.create_date,{}),
                            "scheduled_date":dateObj.value_to_html(picking.scheduled_date,{}),
                            "lat": picking.partner_id.partner_latitude and str(picking.partner_id.partner_latitude) or "",
                            "long":picking.partner_id.partner_longitude and str(picking.partner_id.partner_longitude) or "",
                        }
                        picking_data.update({"warehouse_details":warehouse_data})
                        result['picking_details'].append(picking_data)
            else:
                result = {'success': False, 'message': 'Order not found !!!'}
            response.update(result)
        return self._response('orders', response)

    @route('/mobikul/my/addresses', csrf=False, type='http', auth="none", methods=['POST'])
    def getMyAddresses(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            context = response.get("context")
            Partner = context.get("partner") if not context.get('is_guest') else context.get('order').partner_id
            if Partner:
                result = {}
                domain = [
                    ('id', 'child_of', Partner.commercial_partner_id.ids),
                    ('id', 'not in', [Partner.id]),
                ]
                result['tcount'] = Partner.search_count(domain) + 1
                addresses = Partner.search(domain, limit=self._mData.get('limit', response.get(
                    'itemsPerPage', 5)), offset=self._mData.get('offset', 0),  order="id desc")
                result['addresses'] = [
                    {
                        'name': Partner.name,
                        'url': "/mobikul/my/address/%s" % Partner.id,
                        'addressId': Partner.id,
                    }
                ]
                if self._checkFullAddress(Partner):
                    result['addresses'][0]['display_name'] = self.mobikul_display_address(
                        Partner._display_address(), Partner.name)
                else:
                    result['addresses'][0]['display_name'] = EMPTY_ADDRESS
                # In result['addresses'][0] zero index address is billing address other is shipping address
                for address in addresses:
                    temp = {
                        'name': address.name,
                        'display_name': address._display_address() != EMPTY_ADDRESS and self.mobikul_display_address(address._display_address(), address.name) or address._display_address(),
                        'url': "/mobikul/my/address/%s" % address.id,
                        'addressId': address.id,
                    }
                    if Partner.default_shipping_address_id:
                        if Partner.default_shipping_address_id.id==address.id:
                            result['default_shipping_address_id'] = temp
                    result['addresses'].append(temp)
                    result['message'] = "Address lists"
                if not result.get('default_shipping_address_id',False):
                    result['default_shipping_address_id'] = result['addresses'][0]
            else:
                result = {'success': False, 'message': 'Customer not found !!!'}
            response.update(result)
        return self._response('orders', response)

    @route('/mobikul/my/address/default/<int:address_id>', csrf=False, type='http', auth="none", methods=['PUT'])
    def setDefaultAddress(self, address_id, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            Partner = response.get("context").get("partner").sudo()
            Address = Partner.sudo().browse(address_id)
            if Address and (address_id in Partner.child_ids.ids or address_id == Partner.id):
                Partner.write({"default_shipping_address_id":address_id})
                response.update({'message': 'Updated successfully.'})
            else:
                response.update({'success': False, 'message': 'Address not found !!!'})
        return self._response('address', response)

    @route('/mobikul/my/address/new', csrf=False, type='http', auth="none", methods=['POST'])
    def addMyAddress(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        local = response.get("context",{})
        if response.get('success'):
            Order = local.get('order')
            PartnerObj = local.get("partner").sudo()
            vals = {
                "name": self._mData.get('name', ""),
                "street": self._mData.get('street', ""),
                "zip": self._mData.get('zip', ""),
                "city": self._mData.get('city', ""),
                "phone": self._mData.get('phone', "")
            }
            try:
                if self._mData.get("state_id"):
                    if request.env['res.country.state'].sudo().browse(int(self._mData["state_id"])).exists():
                        vals["state_id"] = int(self._mData["state_id"])
                if self._mData.get("country_id"):
                    if request.env['res.country'].sudo().browse(int(self._mData["country_id"])).exists():
                        vals["country_id"] = int(self._mData["country_id"])
                if local.get('is_guest'):
                    vals.update({"email":self._mData.get('email', ""),"company_name":self._mData.get('company_name', ""),"vat":self._mData.get('vat', "")})
                    parentGuestAddress_id = Order.partner_id.id
                    if Order.partner_id.id == 4:
                        partner_id = PartnerObj.create(vals)
                        Order.write({"partner_id": partner_id.id, "team_id": local.get("teamId")})
                    else:
                        vals.update({"type": "delivery","commercial_partner_id": parentGuestAddress_id,"parent_id": parentGuestAddress_id})
                        PartnerObj.create(vals)
                else:
                    if self._checkFullAddress(PartnerObj):
                        vals.update({"type": "delivery","commercial_partner_id": int(response.get('customerId')),"parent_id": int(response.get('customerId'))})
                        PartnerObj.sudo().create(vals)
                    else:
                        PartnerObj.sudo().write(vals)
                result = {'message': 'Created successfully.'}
            except Exception as e:
                result = {'success': False, 'message': 'Error: Invalid Data < %r >' % e}
            response.update(result)
        return self._response('address', response)

    @route('/mobikul/my/address/<int:address_id>', csrf=False, type='http', auth="none", methods=['POST', 'PUT', 'DELETE'])
    def getMyAddress(self, address_id, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            context = response.get("context")
            PartnerObj = context.get("partner") if not context.get('is_guest') else context.get('order').partner_id
            Address = PartnerObj.search([("id","=",address_id)]).sudo()
            if Address:
                if request.httprequest.method in ["POST"]:
                    result = {
                        'name': Address.name or "",
                        'street': Address.street or "",
                        'zip': Address.zip or "",
                        'city': Address.city or "",
                        'state_id': Address.state_id and Address.state_id.id or "",
                        'country_id': Address.country_id and Address.country_id.id or "",
                        'phone': Address.phone or "",
                    }
                elif request.httprequest.method == "PUT":
                    Address.name = self._mData.get('name', Address.name)
                    Address.street = self._mData.get('street', Address.street)
                    Address.zip = self._mData.get('zip', Address.zip)
                    Address.city = self._mData.get('city', Address.city)
                    Address.phone = self._mData.get('phone', Address.phone)
                    try:
                        if self._mData.get("state_id"):
                            if request.env['res.country.state'].sudo().browse(int(self._mData["state_id"])).exists():
                                Address.state_id = int(self._mData["state_id"])
                        if self._mData.get("country_id"):
                            if request.env['res.country'].sudo().browse(int(self._mData["country_id"])).exists():
                                Address.country_id = int(self._mData["country_id"])
                        result = {'message': 'Updated successfully.'}
                    except Exception as e:
                        result = {'success': False, 'message': 'Error: Invalid Data'}
                elif request.httprequest.method == "DELETE":
                    if response.get('customerId') != address_id and PartnerObj.id != address_id:
                        Address.active = False
                        result = {'message': 'Deleted successfully.'}
                    else:
                        result = {'success': False, 'message': _(
                            'Error: You can`t delete Billing Address.')}
            else:
                result = {'success': False, 'message': 'Address not found !!!'}
            response.update(result)
        return self._response('address', response)

    @route('/mobikul/my/account', csrf=False, type='http', auth="none", methods=['POST'])
    def getMyAccount(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            Partner = response.get("context").get("partner")
            if Partner:
                result = {
                    'name': {'required': True, 'label': _("Your name"), 'value': Partner.name or ""},
                    'email': {'required': True, 'readonly': True, 'label': _("Email"), 'value': Partner.email or ""},
                    'phone': {'label': _("Phone"), 'value': Partner.phone or ""},
                    'street': {'label': _("Street"), 'value': Partner.street or ""},
                    'street2': {'label': _("Street2"), 'value': Partner.street2 or ""},
                    'city': {'label': _("City"), 'value': Partner.city or ""},
                    'zip': {'label': _("Zip / Postal Code"), 'value': Partner.zip or ""},
                    'country_id': {'label': _("Country"), 'value': Partner.country_id and Partner.country_id.id or ""},
                    'state_id': {'label': _("State"), 'value': Partner.state_id and Partner.state_id.id or ""},
                }
                result['message'] = "My Account Details."
            else:
                result = {'success': False, 'message': 'Account not found !!!'}
            response.update(result)
        return self._response('account', response)

    @route('/mobikul/localizationData', csrf=False, type='http', auth="public", methods=['POST'])
    def getLocalizationData(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            Mobikul = response.get("context").get("mobikul_obj")
            StateObj = request.env['res.country.state'].sudo()
            countries = Mobikul.fetch_countries()
            if countries:
                result = {'countries': []}
                state_ids = []
                for country in countries:
                    states = []
                    if country['state_ids']:
                        states = StateObj.search_read(
                            [('id', 'in', country['state_ids'])], fields=['name'])
                    result['countries'].append({
                        'id': country['id'],
                        'name': country['name'],
                        'states': states,
                    })
                    result['message'] = "Localization Data."
            else:
                result = {'success': False, 'message': 'Account not found !!!'}
            response.update(result)
        return self._response('account', response)

    def _website_Wishlist(self, customer_id, product_id=False):
        result = []
        wishlists = request.env['product.wishlist'].sudo().search(
            [('partner_id', '=', customer_id)])
        for wishlist in wishlists:
            result.append(wishlist.product_id.id)
        return result

    @route(['/mobikul/mycart', '/mobikul/mycart/<int:line_id>'],website=True, csrf=False, type='http', auth="public", methods=['POST', 'PUT', 'DELETE'])
    def getMyCart(self, line_id=0, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            result = {"message": "Cart Detils."}
            local = response.get('context', {})
            Partner = local.get("partner")
            addons = response.get('addons', {})
            if Partner:
                if request.httprequest.method == "POST":
                    last_order = local.get('order').sudo()
                    if last_order:
                        if(last_order.pricelist_id.id != local.get("pricelist").id):
                            last_order.pricelist_id = local.get("pricelist").id
                            last_order.sudo().action_update_prices()
                        #last_order._remove_delivery_line()
                        result = {
                            "name": last_order.name,
                            "subtotal": {"title": _("Subtotal"),
                                         "value": _displayWithCurrency(local.get('lang_obj'), last_order.amount_untaxed, local.get('currencySymbol'), local.get('currencyPosition')),
                                         },
                            "tax": {"title": _("Taxes"),
                                    "value": _displayWithCurrency(local.get('lang_obj'), last_order.amount_tax, local.get('currencySymbol'), local.get('currencyPosition')),
                                    },
                            "grandtotal": {"title": _("Total"),
                                           "value": _displayWithCurrency(local.get('lang_obj'), last_order.amount_total, local.get('currencySymbol'), local.get('currencyPosition')),
                                           },
                            "items": []
                        }
                        for item in last_order.order_line:
                            if addons.get('delivery') and item.is_delivery:
                                shippingMethod = {
                                    "tax": [tax.name for tax in item.tax_id],
                                    "name": item.order_id.carrier_id.name,
                                    "description": item.order_id.carrier_id.website_description or "",
                                    "shippingId": item.order_id.carrier_id.id,
                                    "total": _displayWithCurrency(local.get('lang_obj'), item.price_subtotal,local.get('currencySymbol'), local.get('currencyPosition')),
                                }
                                result.update({"delivery": shippingMethod})
                            else:
                                comb_info = item.product_id.product_tmpl_id._get_combination_info(combination=False, product_id=item.product_id.id,add_qty=1,parent_combination=False, only_template=False)   #$$$$
                                temp = {
                                    "lineId": item.id,
                                    "templateId": item.product_id and item.product_id.product_tmpl_id.id or "",
                                    "name": item.product_id and item.product_id.display_name or item.name,
                                    "thumbNail": _get_image_url(self.base_url, 'product.product', item.product_id and item.product_id.id or "", 'image_1920', item.product_id and item.product_id.write_date),
                                    'priceReduce'	: comb_info['has_discounted_price'] and _displayWithCurrency(local.get('lang_obj'), comb_info['price'], local.get('currencySymbol'), local.get('currencyPosition')) or "",
                                    "priceUnit": _displayWithCurrency(local.get('lang_obj'), comb_info['has_discounted_price'] and comb_info['list_price'] or comb_info['price'], local.get('currencySymbol'), local.get('currencyPosition')),
                                    "qty": item.product_uom_qty,
                                    "total": _displayWithCurrency(local.get('lang_obj'), item.price_subtotal, local.get('currencySymbol'), local.get('currencyPosition')),
                                    "discount": item.discount and "(%d%% OFF)" % item.discount or "",
                                }
                                result['items'].append(temp)
                        if not len(result['items']):
                            result['message'] = _('Your Shopping Bag is empty.')
                    else:
                        result = {'message': _('Your Shopping Bag is empty.')}
                else:
                    Order_id = local.get('order').sudo()
                    OrderLineObj = Order_id.order_line
                    OrderLine = OrderLineObj.search([("id","=",line_id)]).sudo()
                    if Order_id:
                        if request.httprequest.method == "PUT":
                            result = {'message': 'Updated successfully.'}
                            add_qty = None
                            set_qty = None
                            if self._mData.get('set_qty'):
                                set_qty = self._mData['set_qty']
                            elif self._mData.get('add_qty'):
                                add_qty = int(self._mData['add_qty'])

                            if add_qty or set_qty:
                                try:
                                    resp = Order_id.with_context(local)._cart_update(
                                        product_id=OrderLine.product_id.id,
                                        line_id=OrderLine.id,
                                        add_qty=add_qty and int(add_qty) or 0,
                                        set_qty=set_qty and int(set_qty) or 0,
                                        product_custom_attribute_values=False,
                                        no_variant_attribute_values=False
                                    )
                                    if addons.get('website_sale_stock') and resp.get('warning'):
                                        raise UserError(resp['warning'])
                                except UserError as ue:
                                    result = {'success': False, 'message': ue.args[0]}
                            else:
                                result = {'message': 'Wrong request.'}
                        elif request.httprequest.method == "DELETE":
                            try:
                                result = {'message': '%s' % (
                                    OrderLine.product_id and OrderLine.product_id.name or OrderLine.name)+_(' was removed from your Shopping Bag.')}
                                OrderLine.unlink()
                            except:
                                result = {'message': 'Please try again after some time.'}
                        else:
                            result = {'message': 'Wrong request.'}
                    else:
                        result = {'message': 'No matching product found !!!'}
            else:
                result = {'success': False, 'message': 'Account not found !!!'}
            response.update(result)
        return self._response('cart', response)

    @route('/mobikul/mycart/setToEmpty', csrf=False, type='http', auth="none", methods=['DELETE'])
    def setToEmpty(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            result = {}
            local = response.get('context', {})
            Partner = local.get("partner")
            if Partner:
                last_order = local.get('order')
                if last_order:
                    try:
                        result = {'message': _('Your Shopping Bag has been set to Empty.')}
                        last_order.order_line.unlink()
                        result['cartCount'] = last_order.cart_count
                    except:
                        result = {'message': 'Please try again after some time.'}
                else:
                    result = {'message': _('Your Shopping Bag is already empty.')}
            else:
                result = {'success': False, 'message': 'Account not found !!!'}
            response.update(result)
        return self._response('setToEmpty', response)

    @route('/mobikul/mycart/addToCart', csrf=False, type='http',website=True, auth="none", methods=['POST'])
    def addToCart(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            context = response.get("context")
            Mobikul = context.get("mobikul_obj")
            result = Mobikul.add_to_cart(self._mData.get("productId"), self._mData.get(
                "set_qty"), self._mData.get("add_qty"), context)
            response.update(result)
        return self._response('addToCart', response)

    @route('/mobikul/re-order/<int:order_id>', csrf=False, type='http', auth="none", methods=['POST'])
    def reOrder(self, order_id = False, **kwargs):
        """
        Will add the already placed order products to the current or new cart.
        order_id = Integer
        """
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            if order_id:
                context = response.get("context")
                Mobikul = context.get("mobikul_obj")
                Partner = context['partner']
                Order = Partner.env['sale.order'].sudo().search([('id','=',order_id)])
                product_domain = _get_product_domain()
                result = {}
                success = 0
                failure = 0
                if Order:
                    if not self._mData.get("needCartMerge"):
                        Partner.last_mobikul_so_id.order_line.unlink()
                    for order in Order.order_line:
                        product_id = order.product_id.id
                        temp_product_domain = product_domain + [("id", "=", product_id)]
                        # Checking if the product is a valid and saleable product and not other offer or shipping added product
                        # TODO Get the correct and effecient way to check the valid products
                        valid_product = request.env['product.product'].sudo().search_count(temp_product_domain)
                        if valid_product:
                            result = Mobikul.add_to_cart(product_id, 0, order.product_uom_qty, context)
                            if not result['success']:
                                failure += 1
                            else:
                                success += 1
                        temp_product_domain = product_domain
                    if (success > 0 and failure == 0) or (success == 0 and failure == 0):
                        result = {'success': True, 'message':  _('Added Successfully')}
                    elif success > 0 and failure > 0:
                        result = {'success': True, 'message': _("Some products were couldn't be added to the cart")}
                    elif success == 0 and failure > 0:
                        result = {'success': False, 'message': _("Cannot re-order the products. Please try again later")}
                else:
                    result = {'success': False, 'message': _("Order doesn't belong to the current user or doesn't exits. Please provide the correct order Id")}
            else:
                result = {'success': False, 'message': _('Please provide the order Id')}
            response.update(result)
        return self._response('reOrder', response)


    @route(['/mobikul/ShippingMethods'], csrf=False, type='http', auth="none", methods=['GET'])
    def getAvailableShippingMethods(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            if response.get('addons', {}).get('delivery'):
                context =  response.get("context",{})
                Partner = context.get("partner")
                SaleOrder = Partner.with_context(**context).last_mobikul_so_id if not (context.get('is_guest')) else context.get('tokenObj').last_guest_so_id
                ShippingMethods = SaleOrder and SaleOrder.sudo()._get_delivery_methods() or False
                if ShippingMethods:
                    result = []
                    for method in ShippingMethods:
                        result.append({
                            "name": method.name,
                            "id": method.id,
                            "description": method.website_description or "",
                            "price": _displayWithCurrency(context.get('lang_obj'), method.rate_shipment(SaleOrder).get('price'),
                                                          context.get('currencySymbol', ""), context.get('currencyPosition', "")),
                        })
                    result = {'ShippingMethods': result, "message": "Shipping methods list"}
                else:
                    result = {'success': False, 'message': 'No Active Shipping methods found.'}
            else:
                result = {'success': False, 'message': 'Website Sale Delivery is not install.'}
            response.update(result)
        return self._response('getAvailableShippingMethods', response)

    @route('/mobikul/paymentAcquirers', csrf=False, type='http', auth="none", methods=['POST'])
    def getPaymentAcquirer(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            result = {}
            AcquirerObj = request.env['payment.provider'].sudo()
            Acquirers = AcquirerObj.search_read([('is_mobikul_available', '=', 1), ('mobikul_reference_code', 'in', AQUIRER_REF_CODES)], fields=[
                'name', 'pre_msg', 'mobikul_reference_code', 'mobikul_extra_key', 'write_date'])
            if Acquirers:
                result = {'acquirers': Acquirers}
                for index, value in enumerate(result['acquirers']):
                    result['acquirers'][index]['thumbNail'] = _get_image_url(
                        self.base_url, 'payment.acquirer', result['acquirers'][index]['id'], 'image_128', result['acquirers'][index]['write_date'])
                    result['acquirers'][index]['description'] = result['acquirers'][index].pop('pre_msg') and remove_htmltags(
                        result['acquirers'][index].pop('pre_msg')) or ""
                    result['acquirers'][index]['code'] = result['acquirers'][index].pop(
                        'mobikul_reference_code') or ""
                    result['acquirers'][index]['extraKey'] = result['acquirers'][index].pop(
                        'mobikul_extra_key') or ""
                    result['acquirers'][index].pop('write_date', None)
                result['message'] = "Payment Acquirer list."
            else:
                result = {'success': False, 'message': 'No Active Payment methods found.'}
            response.update(result)
        return self._response('paymentAcquirer', response)

    @route('/mobikul/orderReviewData', csrf=False, type='http', auth="public",website=True, methods=['POST'])
    def getOrderReviewData(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            context = response.get("context",{})
            Mobikul = context.get("mobikul_obj")
            paymentTerms = Mobikul._getPaymentTerms()
            response.update(paymentTerms)
            Acquirer = request.env['payment.provider'].sudo().search([("id","=",self._mData.get('acquirerId') and int(self._mData['acquirerId']))])
            if Acquirer:
                user = context.get("user")
                if user:
                    try:
                        if response.get('addons', {}).get('email_verification') and context.get("websiteObj").restrict_unverified_users:
                            if user.wk_token_verified:
                                response.update(self._orderReview(user, response, Acquirer))
                            else:
                                response.update({'success': False, 'message': _(
                                    "You can't place your order, please verify your account")})
                        else:
                            response.update(self._orderReview(user, response, Acquirer))
                    except ValidationError as ve:
                        response.update({'success': False, 'message': ve.args[0]})
                else:
                    response.update({'success': False, 'message': _('Account not found !!!')})
            else:
                response.update({'success': False, 'message': _(
                    'No Payment methods found with given id.')})
        return self._response('orderReviewData', response)

    @route('/mobikul/placeMyOrder', csrf=False, type='http', auth="none",website=True, methods=['POST'])
    def placeMyOrder(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        context = response.get('context')
        if response.get('success'):
            if self._mData.get('transaction_id'):
                response.update(self.placeOrder(context))
            else:
                response.update({'success': False, 'message': _('Transaction Id not found !!!')})
        return self._response('placeMyOrder', response)


    @route('/mobikul/delete/account', csrf=False, type='http', auth="public", methods=['POST'])
    def delete_account(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            user_id = response.get("userId")
            User = request.env['res.users'].sudo().browse(user_id)
            result = {}
            if User and User.id not in ADMIN_USER:
                try:
                    vals = self.anonymize_details(user=True,s_login=True) if User.oauth_provider_id else self.anonymize_details(user=True)
					# generate random no so that anonymized login is unique
                    random_no = fields.datetime.now().strftime('%Y-%m-%d-%H:%M:%S').replace(" ", "")
                    random_login = 'OdooUser@' + random_no
                    vals.update({"login":random_login})
                    User.write(vals)
                    User.partner_id.write(self.anonymize_details())
                    self._removeAddress(User.partner_id)
                    self._tokenUpdate()
                    result = {'success': True, 'message': 'User account successfully anonymized !!!'}
                except Exception as e:\
                    result = {'success': False, 'message': e.args[0]}
            else:
                result = {'success': False, 'message': "User Cannot Be Deleted !!!"}
        else:
            result = {'success': False, 'message': response.get('message','Something went wrong. Please retry.')}
        response.update(result)
        return self._response('delete_account', response)



    @route('/mobikul/deleteProfileImage', csrf=False, type='http', auth="none", methods=['DELETE'])
    def deleteProfileImage(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            result = {}
            User = response.get("context").get("user")
            if User:
                User.write({'image_1920': False})
                response.update({"message": _("Profile Image Deleted Successfully.")})
            else:
                response.update({'success': False, 'message': _('Account not found !!!')})
        return self._response('deleteProfileImage', response)

    @route('/mobikul/delete/customer/banner-image', csrf=False, type='http', auth="none", methods=['DELETE'])
    def deleteCustomerBannerImage(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            result = {}
            Partner = response.get("context").get('partner').sudo()
            if Partner:
                Partner.write({'banner_image': False})
                response.update({"message": _("Banner Image Deleted Successfully.")})
            else:
                response.update({'success': False, 'message': _('Account not found !!!')})
        return self._response('deleteCustomerBannerImage', response)

    @route('/mobikul/saveMyDetails', csrf=False, type='http', auth="none", methods=['POST'])
    def saveMyDetails(self, **kwargs):

        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            result = {}
            context = response.get('context',{})
            base_url = context.get("base_url")
            User = context.get('user').sudo()
            if User and not context.get('is_guest'):
                result['message'] = _("Updated Successfully.")
                data = {}
                if self._mData.get('image'):
                    data['image_1920'] = self._mData['image']
                if self._mData.get('name'):
                    data['name'] = self._mData['name']
                if self._mData.get('password'):
                    data['password'] = self._mData['password']
                try:
                    Partner = context.get('partner').sudo()
                    if self._mData.get('bannerImage'):
                        Partner.banner_image = self._mData['bannerImage']
                    User.write(data)
                    result['customerBannerImage'] = _get_image_url(
                        base_url,
                        'res.partner',
                        Partner.id,
                        'banner_image',
                        Partner.write_date
                    )
                    result['customerProfileImage'] = _get_image_url(
                        base_url,
                        'res.partner',
                        Partner.id,
                        'image_1920',
                        Partner.write_date
                    )
                except Exception as e:
                    result = {'success':False, 'message': _("Please try again later,")+" %r" % e.args[0]}
            else:
                result = {'success': False, 'message': _('Account not found !!!')}
            response.update(result)
        return self._response('saveMyDetails', response)

    @route('/mobikul/registerFcmToken', csrf=False, type='http', auth="public", methods=['POST'])
    def registerFcmToken(self, **kwargs):
        response = self._authenticate(False, **kwargs)
        if response.get('success'):
            customer_id = False
            if self._mData.get("customerId"):
                customer_id = int(self._mData["customerId"])
            self._tokenUpdate(customer_id=customer_id)
            response.update({'message': _('Request completed !')})
        return self._response('registerFcmToken', response)

    @route('/mobikul/notificationMessages', csrf=False, type='http', auth="none", methods=['POST'])
    def getNotificationMessages(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            Partner = response.get('context',{}).get('partner')
            fields = ['id', 'name', 'title', 'subtitle', 'body', 'banner',
                      'icon', 'period', 'datatype', 'is_read', 'write_date']
            domain = [('customer_id', '=', Partner.id)]
            Message = request.env['mobikul.notification.messages']
            notification_message = Message.search_read(domain, limit=self._mData.get('limit', response.get(
                'itemsPerPage', 5)), offset=self._mData.get('offset', 0),  order="id desc", fields=fields)
            for msg in notification_message:
                msg['name'] = msg['name'] or ""
                msg['title'] = msg['title'] or ""
                msg['subtitle'] = msg['subtitle'] or ""
                msg['body'] = msg['body'] or ""
                msg['icon'] = _get_image_url(
                    self.base_url, 'mobikul.notification.messages', msg['id'], 'icon', msg['write_date'])
                msg['banner'] = _get_image_url(
                    self.base_url, 'mobikul.notification.messages', msg['id'], 'banner', msg['write_date'])
                msg.pop('write_date')
            result = {'all_notification_messages': notification_message}
            response.update(result)

        return self._response('notificationMessages', response)

    @route('/mobikul/notificationMessage/<int:message_id>', csrf=False, type='http', auth="none",  methods=['POST', 'PUT', 'DELETE'])
    def getNotificationMessageDetails(self, message_id, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            Partner = response.get('context',{}).get('partner')
            MessageObj = request.env['mobikul.notification.messages']
            message = MessageObj.search(
                [('id', '=', message_id), ('customer_id', '=', response.get('customerId'))]).sudo()
            if message:
                if request.httprequest.method == "POST":
                    message.sudo().is_read = True
                    result = {
                        'id': message.id,
                        'name': message.name or "",
                        'create_date': Datetime.to_string(message.create_date),
                        'title': message.title or "",
                        'subtitle': message.subtitle or "",
                        'body': message.body or "",
                        'icon': _get_image_url(self.base_url, 'mobikul.notification.messages', message.id, 'icon', message.write_date),
                        'banner': _get_image_url(self.base_url, 'mobikul.notification.messages', message.id, 'banner', message.write_date),
                        'period': message.period,
                        'is_read': message.is_read,
                        'datatype': message.datatype,
                        'success': True,
                        'message': 'Successfull'
                    }
                elif request.httprequest.method == "DELETE":
                    message.sudo().active = False
                    result = {'success': True, 'message': _('Deleted Successfully')}
                elif request.httprequest.method == "PUT":
                    message.sudo().is_read = self._mData.get('is_read', message.is_read)
                    result = {'success': True, 'message': _('Updated Successfully')}
            else:
                result = {'success': False, 'message': _('Message not Found')}
            response.update(result)
        return self._response('notificationMessageDetails', response)

    @route('/mobikul/my/wishlists', csrf=False, type='http', auth="public",website=True, methods=['POST'])
    def getMyWishlists(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            if response.get('addons', {}).get('wishlist') and response.get('customerId'):
                wishlists = []
                Partner = response.get("context").get("partner")
                local = response.get('context', {})
                for wishlist in Partner.wishlist_ids:
                    product_id = wishlist.product_id.sudo()
                    if product_id:
                        comb_info = product_id.product_tmpl_id._get_combination_info(combination=False, product_id=product_id.id,add_qty=1,parent_combination=False, only_template=False)   #$$$$
                        product_detail = {
                            'id': wishlist.id,
                            "name": wishlist.product_id.display_name,
                            "thumbNail": _get_image_url(self.base_url, 'product.product', wishlist.product_id.id, 'image_1920', wishlist.product_id.write_date),
                            "priceReduce": comb_info['has_discounted_price'] and _displayWithCurrency(local.get('lang_obj'), comb_info['price'], local.get('currencySymbol'), local.get('currencyPosition')) or "",
                            "priceUnit": _displayWithCurrency(local.get('lang_obj'), comb_info['has_discounted_price'] and comb_info['list_price'] or comb_info['price'], local.get('currencySymbol'), local.get('currencyPosition')),
                            "productId": wishlist.product_id.id,
                            "templateId": wishlist.product_id.product_tmpl_id.id,

                        }
                        wishlists.append(product_detail)
                result = {
                    'success': True,
                    "wishLists": wishlists,
                    'message': 'success'
                }
            else:
                result = {'success': False, 'message': 'Wishlist is not Active !!!'}
            response.update(result)
        return self._response('myWishlists', response)

    @route('/my/removeWishlist/<int:wishlist_id>', csrf=False, type='http', auth="none",  methods=['DELETE'])
    def removeWishlist(self, wishlist_id, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            if response.get('addons', {}).get('wishlist'):
                result = {'success': False, 'message': 'Wishlist Id Not Found'}
                try:
                    wishlist = request.env['product.wishlist'].sudo().search(
                        [('id', '=', wishlist_id), ('partner_id', '=', response.get('customerId'))])
                    if wishlist:
                        wishlist.unlink()
                        result.update({'success': True,
                                       'message': 'Item removed'
                                       })
                except Exception as e:
                    result.update({
                        'success': False,
                        'message': 'Please try again later %r' % e.args[0],
                    })
            else:
                result = {'success': False, 'message': 'Wishlist is not Active !!!'}
            response.update(result)
        return self._response('removeWishlist', response)

    @route('/my/removeFromWishlist/<int:product_id>', csrf=False, type='http', auth="none",  methods=['DELETE'])
    def removeFromWishlist(self, product_id, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            if response.get('addons', {}).get('wishlist'):
                result = {
                    'success': False,
                    'message': 'ProductId Not Found in wishlist',
                }
                try:
                    wishlist = request.env['product.wishlist'].sudo().search(
                        [('product_id', '=', product_id), ('partner_id', '=', response.get('customerId'))])
                    if wishlist:
                        wishlist.unlink()
                        result.update({'success': True, 'message': 'Item removed'})
                except Exception as e:
                    result.update({'success': False, 'message': 'Please try again later %r' % e.args[0]})
            else:
                result = {'success': False, 'message': 'Wishlist is not Active !!!'}
            response.update(result)
        return self._response('removeFromWishlist', response)

    @route('/my/addToWishlist', csrf=False, type='http', auth="none",website=True, methods=['POST'])
    def addToWishlist(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            if response.get('addons', {}).get('wishlist') and response.get('customerId'):
                result = self.add2Ws(response.get("context"), self._mData.get("productId"))
            else:
                result = {'success': False, 'message': 'Wishlist is not Active !!!'}
            response.update(result)
        return self._response('addToWishlist', response)

    @route('/my/wishlistToCart', csrf=False, type='http', auth="none", methods=['POST'])
    def moveWishlistToCart(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            if response.get('addons', {}).get('wishlist') and response.get('customerId'):
                wishlistObj = request.env['product.wishlist'].sudo()
                wishlist = wishlistObj.search(
                    [('id', '=', self._mData.get("wishlistId")), ('partner_id', '=', response.get('customerId'))])
                result = request.env['mobikul'].sudo().add_to_cart(
                    wishlist.product_id.id, 0, self._mData.get("add_qty", 1), response.get("context"))
                if result.get("success"):
                    wishlist.unlink()
                    result = {'success': True, 'message': _('Item moved to Bag')}
                else:
                    result = {'success': False, 'message': result.get('message', _('Please try again later'))}
            else:
                result = {'success': False, 'message': _('Wishlist is not Active !!!')}
            response.update(result)
        return self._response('moveWishlistToCart', response)

    @route('/my/cartToWishlist', csrf=False, type='http', auth="none",website=True, methods=['POST'])
    def moveCartToWishlist(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            if response.get('addons', {}).get('wishlist'):
                OrderLine = request.env['sale.order.line'].sudo().search(
                    [('id', '=', self._mData.get('line_id'))])
                if OrderLine:
                    result = self.add2Ws(response.get('context'), OrderLine.product_id.id)
                    if result.get("success"):
                        OrderLine.unlink()
                else:
                    result = {'success': False, 'message': _('Order not found')}
            else:
                result = {'success': False, 'message': 'Wishlist is not Active !!!'}
            response.update(result)
        return self._response('moveCartToWishlist', response)

    @route('/mobikul/signup/terms', csrf=False, type='http', auth="public", methods=['GET'])
    def signupTermsCondition(self, **kwargs):
        response = self._authenticate(False, **kwargs)
        Mobikul = response.get("context").get("mobikul_obj")
        if response.get('success'):
            response.update(
                {'success': True, 'termsAndConditions': Mobikul.signup_terms_and_condition})
        else:
            response.update(
                {'success': False, 'message': "signup Terms and conditions is disable."})
        return self._response('signupTermsCondition', response)

    @route('/product/reviews', csrf=False, type='http', auth="public", methods=['POST'])
    def getProductReview(self, **kwargs):
        response = self._authenticate(False, **kwargs)
        if response.get('success'):
            if response.get('addons', {}).get('review'):

                product_reviews = []
                reviewObj = request.env['user.review'].sudo()
                domain = [('template_id', '=', self._mData.get(
                    'template_id')), ('state', '=', 'pub')]
                fields = ['customer', 'customer_image', 'email', 'likes', 'dislikes',
                          'rating', 'title', 'msg', 'create_date', 'partner_id', 'write_date']
                product_reviews = reviewObj.search_read(domain, limit=self._mData.get('limit', response.get(
                    'itemsPerPage', 5)), offset=self._mData.get('offset', 0),  order="id desc", fields=fields)
                for review in product_reviews:

                    review['customer_image'] = _get_image_url(
                        self.base_url, 'user.review', review['id'], 'customer_image',review['write_date'])
                    review['create_date'] = _easy_date(review['create_date'])
                    review['write_date'] = Datetime.to_string(review['write_date'])
                    if response.get('addons', {}).get('email_verification'):
                        res_partner = request.env['res.partner'].sudo().browse(
                            review.get('partner_id') and review.get('partner_id')[0])
                        del review['partner_id']
                        review['is_email_verified'] = res_partner and res_partner.user_ids and res_partner.user_ids.wk_token_verified or False
                result = {'product_reviews': product_reviews, "reviewCount": len(product_reviews)}

            else:
                result = {'success': False, 'message': _('Review Module not install !!!')}
            response.update(result)
        return self._response('ProductReview', response)

    @route('/my/saveReview', csrf=False, type='http', auth="none", methods=['POST'])
    def addReview(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            Mobikul = response.get("context").get("mobikul_obj")
            result = {}
            if response.get('addons', {}).get('review'):
                Partner = response.get("context").get("partner")
                if Partner:
                    vals = {
                        "title": self._mData.get("title"),
                        'msg': self._mData.get("detail"),
                        "rating": self._mData.get("rate"),
                        'partner_id': Partner.id,
                        "template_id": self._mData.get("template_id"),
                        "customer": Partner.name,
                        "email": Partner.email,
                        "customer_image": Partner.image_1920
                    }
                    try:
                        Partner.env['user.review'].sudo().create(vals)
                        if Mobikul.review_defaults().get('auto_publish'):
                            result = {'success': True, 'message': _('Thanks for your review.')}
                        else:
                            result = {'success': True, 'message': Mobikul.review_defaults().get(
                                'message_when_unpublish')}
                    except Exception as e:
                        result = {'success': False, 'message': _('Please try again later')}
                else:
                    result = {'success': False, 'message': _('Account not found !!!')}
            else:
                response.update({'success': False, 'message': _('Review Module not install !!!')})
            response.update(result)
        return self._response('addReview', response)

    @route('/review/likeDislike', csrf=False, type='http', auth="none", methods=['POST'])
    def addLikeDislike(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        likeDislikeObj = request.env['review.like.dislike'].sudo()
        # it assume that review module is installed
        if response.get('success') and self._mData.get("review_id"):
            review = request.env['user.review'].sudo().search([("partner_id","=",response.get("customerId")),("id","=",int(self._mData.get("review_id")))])
            if review:
                ld_exist = likeDislikeObj.search(
                    [("customer_id", "=", response.get('userId')), ("review_id", "=", review.id)])
                vals = {
                    "customer_id": response.get('userId'),
                    'like': self._mData.get("ishelpful"),
                    "dislike": not self._mData.get("ishelpful"),
                    'review_id': review.id,
                }
                if ld_exist:
                    try:
                        ld_exist.write(vals)
                        result = {'success': True, 'message': _('Thank you for your feedback.')}
                    except Exception as e:
                        result = {'success': False, 'message': _('Please try again later')}
                else:
                    try:
                        likeDislikeObj.sudo().create(vals)
                        result = {'success': True, 'message': _('Thank you for your feedback.')}
                    except Exception as e:
                        result = {'success': False, 'message': _('Please try again later')}
            else:
                result = {'success': False, 'message': _('Review not found !!!')}
            response.update(result)
        else:
            response["message"] = _("You need to login first !")
        return self._response('addLikeDislike', response)

    @route('/send/verifyEmail', csrf=False, type='http', auth="none", methods=['POST'])
    def verifyEmail(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        Mobikul = response.get("context").get("mobikul_obj")
        context = response.get("context",{})
        if response.get('success'):
            if response.get('addons', {}).get('email_verification') :
                user = response.get("context").get("user").sudo()
                if not user.wk_token_verified:
                    user.send_verification_email(user.id)
                    response['message'] = _("Verification email sent successfully.")
                    response['success'] = True
                else:
                    response['message'] = _("Email already verified.")
                    response['success'] = False
            else:
                response.update({'success': False, 'message': _(
                    'Email Verification Module not install !!!')})
        return self._response('verifyEmail', response)

    @route('/my/Template/seller/<int:seller_id>', csrf=False, type='http', auth="public", website=True, methods=['GET'])
    def productSellerInfo(self, seller_id, **kwargs):
        if request.httprequest.headers.get("Login"):
            response = self._authenticate(True, **kwargs)
        else:
            response = self._authenticate(False, **kwargs)
        if response.get('success'):
            if response.get('addons', {}).get('odoo_marketplace'):
                # context = response.get('context', {})
                sellerDetail = self.seller_profile_info(seller_id, response)

                if sellerDetail:
                    result = {'SellerInfo': sellerDetail,
                              'success': True, 'message': _('Seller Found !!!')}
                else:
                    result = {'success': False, 'message': _('Seller Not Found !!!')}
            else:
                result = {'success': False, 'message': _('Marketplace is not Active !!!')}

            if response.get('addons', {}).get('wishlist') and response.get('customerId'):
                wishlists = self._website_Wishlist(response.get('customerId', 0))
                result.update({'wishlists': wishlists})
            response.update(result)
        return self._response('productSellerInfo', response)

    def seller_profile_info(self, seller_id, response):
        MobikulObj = response.get("context").get('mobikul_obj')
        detail = {}
        sellerDetail = request.env['res.partner'].sudo().search(
            [('id', '=', seller_id), ('seller', '=', True)])
        if sellerDetail:
            detail = {
                "seller_id"				: sellerDetail.id,
                'name'					: sellerDetail.name,
                'email'					: sellerDetail.email,
                'average_rating'		: sellerDetail.avg_review(),
                'total_reviews'			: len(sellerDetail.seller_review_ids.filtered(lambda r: (r.active == True and r.state == "pub"))),
                'sales_count'			: sellerDetail.seller_sales_count(),
                'product_count'			: sellerDetail.seller_products_count(),
                'seller_profile_image'	: self.get_marketplace_image_url(self.base_url, 'res.partner', sellerDetail.id, 'profile_image', sellerDetail.write_date),
                'seller_profile_banner'	: self.get_marketplace_image_url(self.base_url, 'res.partner', sellerDetail.id, 'profile_banner', sellerDetail.write_date),
                'create_date'			: Datetime.to_string(sellerDetail.create_date),
                'state'					: sellerDetail.state_id.name or "",
                'country'				: sellerDetail.country_id.name or "",
                'phone'					: sellerDetail.phone or "",
                'mobile'				: sellerDetail.mobile or "",
                'profile_msg'			: remove_htmltags(sellerDetail.profile_msg or ""),
                'return_policy'			: remove_htmltags(sellerDetail.return_policy or ""),
                'shipping_policy'		: remove_htmltags(sellerDetail.shipping_policy or ""),

            }
            seller_review = []
            reviews = sellerDetail.fetch_active_review2(sellerDetail.id, 0, 2)
            seller_review = self.getSellerReviewsDetail(reviews)
            detail.update({'seller_reviews': seller_review})
            self._mData = {"domain": "[('marketplace_seller_id','=',%d)]" % sellerDetail.id,
                            "order": "create_date desc, id desc",
                            "limit": 5}
            cont = response.get("context")
            # if 'pricelist' in cont:
            #     cont.pop("pricelist")
            sellerProducts = MobikulObj.fetch_products(context=cont,**self._mData)

            detail.update({'sellerProducts': sellerProducts})
        return detail

    def getSellerReviewsDetail(self, reviewsObj):
        reviewsDetail = []
        for review in reviewsObj:
            reviewsDetail.append({
                "create_date": Datetime.to_string(review.create_date),
                "rating": review.rating,
                "not_helpful": review.not_helpful,
                "total_votes": review.total_votes,
                "display_name": review.display_name,
                "message_is_follower": review.message_is_follower,
                "title": review.title,
                "id": review.id,
                "msg": review.msg,
                "helpful": review.helpful,
                "email": review.email,
                "name": review.partner_id.name,
                "image": _get_image_url(self.base_url, 'res.partner', review.partner_id.id, 'profile_image', review.partner_id.write_date),
            })
        return reviewsDetail
#
#     # view all the product of sellers api "http://192.168.1.86:8010/mobikul/search"
#     # {"domain": "[('marketplace_seller_id','=',117)]", "offset": 0, "limit":100}
#
    @route('/mobikul/marketplace', csrf=False, type='http', auth="public", website=True, methods=['GET'])
    def marketplace(self, **kwargs):
        PartnerObj = request.env['res.partner'].sudo()
        if request.httprequest.headers.get("Login"):
            response = self._authenticate(True, **kwargs)
        else:
            response = self._authenticate(False, **kwargs)
        if response.get('success'):
            if response.get('addons', {}).get('odoo_marketplace'):
                lst = []
                context = response.get('context', {})
                mobikul = context.get('mobikul_obj')
                website_id = mobikul and mobikul.website_id
                result = {
                    "banner": website_id and website_id.mp_landing_page_banner and _get_image_url(self.base_url, 'website', website_id.id, 'mp_landing_page_banner', website_id.write_date) or self.base_url+"odoo_marketplace/static/src/img/Hero-Banner.png",
                    "heading": _("Still Selling Offline? Start Selling Online."),
                    }
                sellersObj = PartnerObj.search(
                    [('seller', '=', True), ('state', '=', 'approved'), ('website_published', '=', True)], limit=5)
                for seller in sellersObj:
                    sellerDetail = self.seller_profile_info(seller.id, response)
                    lst.append(sellerDetail)
                result.update({'SellersDetail': lst, 'success': True,
                               'message': _('Marketplace page !!!')})
            else:
                result = {'success': False, 'message': _('Marketplace is not Active !!!')}
            response.update(result)
            if response.get('addons', {}).get('wishlist') and response.get('customerId'):
                response['wishlist'] = self._website_Wishlist(response.get('customerId'))
        return self._response('marketplace', response)
#
    def get_marketplace_image_url(self, base_url, model_name, record_id, field_name, write_date, width=0, height=0):
        """ Returns a local url that points to the image field of a given browse record only for marketplace """
        # format of marketplace image url "base_url+/ marketplace / image / 139 / res.partner / profile_banner"
        write_date = re.sub("[^\d]", "", Datetime.to_string(write_date))

        if base_url and not base_url.endswith("/"):
            base_url = base_url + "/"
        if width or height:
            return '%swebsite/image/%s/%s/%s/%sx%s?unique=%s' % (base_url, model_name, record_id, field_name, width, height, write_date)
        else:
            return '%swebsite/image/%s/%s/%s?unique=%s' % (base_url, model_name, record_id, field_name, write_date)

    def checkReviewEligibility(self, seller_id, customer_id):
        """
        this method is responsible for marketplace ['/seller/review/check'] controller
        """

        sol_objs = request.env["sale.order.line"].sudo().search([("product_id.marketplace_seller_id", "=", seller_id), (
            "order_id.partner_id", "=", customer_id), ("order_id.state", "in", ["sale", "done"])])
        for_seller_total_review_obj = request.env["seller.review"].sudo().search(
            [('marketplace_seller_id', '=', seller_id), ('partner_id', '=', customer_id)])

        # This code must be used in create of review
        if len(sol_objs.ids) == 0:
            result = {"success": False, "message": _(
                "You have to purchase a product of this seller first.")}
        elif len(for_seller_total_review_obj.ids) >= len(sol_objs.ids):
            result = {"success": False, "message": _(
                "According to your purchase your review limit is over.")}
        else:
            result = {"success": True, "message": _("Eligible for write a review")}
        return result
#
    @route('/my/review/seller/<int:seller_id>', csrf=False, type='http', auth="none", website=True, methods=['GET', 'POST'])
    def reviewSeller(self, seller_id, **kwargs):
        SellReviewObj = request.env['seller.review'].sudo()
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            if response.get('addons', {}).get('odoo_marketplace'):
                seller = request.env['res.partner'].sudo().search(
                    [('id', '=', seller_id), ('seller', '=', True)])
                if seller:
                    if request.httprequest.method == "GET":
                        sellerReviewDetail = SellReviewObj.search(
                            [('marketplace_seller_id', '=', seller_id), ('active', '=', True), ('state', '=', 'pub')])
                        reviewsDetail = self.getSellerReviewsDetail(sellerReviewDetail)
                        result = {
                            'SellerReview': reviewsDetail,
                            "seller_image": self.get_marketplace_image_url(self.base_url, 'res.partner', seller.id, 'image_1920', seller.write_date),
                            'seller_profile_image': self.get_marketplace_image_url(self.base_url, 'res.partner', seller.id, 'profile_image', seller.write_date),
                            'sellerReviewCount': len(sellerReviewDetail),
                            'success': True,
                            'message': _('Seller Found !!!')
                        }
                    elif request.httprequest.method == "POST":
                        result = self.checkReviewEligibility(seller_id, response.get('customerId'))
                        if result.get('success'):
                            if self._mData.get('msg') and self._mData.get('rating') and self._mData.get('title'):
                                review = {
                                    'msg': self._mData.get('msg'),
                                    'rating': int(self._mData.get('rating')),
                                    'title': self._mData.get('title'),
                                    'marketplace_seller_id': seller_id,
                                    "partner_id": response.get('customerId'),
                                    "website_published":True
                                }
                                review_obj = request.env['seller.review'].sudo().with_context({'mail_create_nosubscribe':True}).create(review)
                                result = {'success': True, 'message': _(
                                    'Review create successfully for seller id')+'%s' % seller_id}
                            else:
                                result = {'success': False, 'message': _(
                                    'Pass the params properly for create review!!!')}
                    else:
                        result = {'success': False, 'message': _('Wrong Request')}
                else:
                    result = {'success': False, 'message': _('Seller not Found.')}

            else:
                result = {'success': False, 'message': 'Marketplace is not Active !!!'}
            response.update(result)
        return self._response('reviewSeller', response)

    @route(['/mobikul/marketplace/seller/review/vote/<int:review_id>'], csrf=False, type='http', auth="none", website=True, methods=['POST'])
    def sellerReviewVote(self, review_id, **kwargs):
        review_help_obj = request.env['review.help'].sudo()
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            if response.get('addons', {}).get('odoo_marketplace'):
                ishelpful = self._mData.get('ishelpful') and "yes" or "no"
                vote_exist = review_help_obj.search(
                    [('seller_review_id', '=', review_id), ('customer_id', '=', response.get('customerId'))])

                if vote_exist:
                    vote_exist[0].write({"review_help": ishelpful,"seller_review_id":review_id})
                    result = {'success': True, 'message': _(
                        'seller review vote update successfully !!!')}
                else:
                    reviewObj = review_help_obj.sudo().create({"customer_id": response.get(
                        'customerId'), "seller_review_id": review_id, "review_help": ishelpful})
                    result = {'success': True, 'message': _(
                        'seller review vote create successfully !!!')}

                reviewObj = request.env['seller.review'].sudo().browse(review_id)
                seller_review = self.getSellerReviewsDetail(reviewObj)
                result["SellerReview"] = seller_review
            else:
                result = {'success': False, 'message': _('Marketplace is not Active !!!')}
            response.update(result)
        return self._response('sellerReviewVote', response)
#
    @route(['/mobikul/marketplace/seller/orderlines'], csrf=False, type='http', auth="none", website=True, methods=['POST'])
    def sellerOrderLines(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            Partner = response.get("context",{}).get("partner")
            if Partner and Partner.seller:
                if response.get('addons', {}).get('odoo_marketplace'):
                    result = {'success': True}
                    context = response.get('context', {})
                    SaleOrderLine = request.env['sale.order.line'].sudo()
                    domain = [('marketplace_seller_id', '=', response.get('customerId'))]
                    if self._mData.get('state'):
                        domain += [('marketplace_state', '=', self._mData.get('state'))]
                    result['tcount'] = SaleOrderLine.search_count(domain)
                    orderline = SaleOrderLine.search(domain, limit=self._mData.get('limit', response.get('itemsPerPage', 5)),
                                                     offset=self._mData.get('offset', 0), order="id desc")
                    result['sellerOrderLines'] = []
                    for order in orderline:
                        temp = {
                            'line_id': order.id,
                            'create_date': Datetime.to_string(order.create_date),
                            'order_reference': order.order_id.id,
                            'customer': order.order_partner_id.name,
                            'product': order.product_id.name,
                            'price_unit': _displayWithCurrency(context.get('lang_obj'), order.price_unit,
                                                               context.get('currencySymbol', ""), context.get('currencyPosition', "")),
                            'quantity': order.product_uom_qty,
                            'sub_total': _displayWithCurrency(context.get('lang_obj'), order.price_subtotal,
                                                              context.get('currencySymbol', ""), context.get('currencyPosition', "")),
                            'delivered_qty': order.qty_delivered,
                            'order_state': order.state,
                            'marketplace_state': order.marketplace_state,
                            'description': order.name,
                        }
                        result['sellerOrderLines'].append(temp)
                else:
                    result = {'success': False, 'message': ('Marketplace is not Active !!!')}
            else:
                result = {'success': False, 'message': ('Customer is not a seller !!!')}
            response.update(result)
        return self._response('sellerOrderLines', response)
#
    @route(['/mobikul/marketplace/seller/orderline/<int:line_id>'], csrf=False, type='http', auth="none", website=True, methods=['GET'])
    def sellerOrderLinesDetail(self, line_id, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            Partner = response.get("context",{}).get("partner")
            if Partner and Partner.seller:
                if response.get('addons', {}).get('odoo_marketplace'):
                    result = {'success': True}
                    context = response.get('context', {})
                    SaleOrderLine = request.env['sale.order.line'].sudo()
                    domain = [('id', '=', line_id),('marketplace_seller_id', '=', response.get('customerId'))]
                    orderline = SaleOrderLine.search(domain)
                    if orderline:
                        result['sellerOrderLineDetail'] = {
                            'line_id': orderline.id,
                            'create_date': Datetime.to_string(orderline.create_date),
                            'order_reference': orderline.order_id.id,
                            'customer': orderline.order_partner_id.name,
                            'product': orderline.product_id.name,
                            'price_unit': _displayWithCurrency(context.get('lang_obj'), orderline.price_unit,
                                                               context.get('currencySymbol', ""),
                                                               context.get('currencyPosition', "")),
                            'quantity': orderline.product_uom_qty,
                            'sub_total': _displayWithCurrency(context.get('lang_obj'), orderline.price_subtotal,
                                                              context.get('currencySymbol', ""),
                                                              context.get('currencyPosition', "")),
                            'delivered_qty': orderline.qty_delivered,
                            'order_state': orderline.state,
                            'marketplace_state': orderline.marketplace_state,
                            'description': orderline.name,
                            'order_payment_acquirer': orderline.order_payment_acquirer_id.id and orderline.order_payment_acquirer_id.id or "",
                            'delivery_method': orderline.order_id.carrier_id and orderline.order_id.carrier_id.id or ""

                        }
                    else:
                        result = {'success': False, 'message': 'Unable to retrieve the requested data'}
                else:
                    result = {'success': False, 'message': 'Marketplace is not Active !!!'}
            else:
                result = {'success': False, 'message': 'Customer is not a seller !!!'}
            response.update(result)
        return self._response('sellerOrderLinesDetail', response)

    # {"domain": "[('marketplace_seller_id','=',65),('status','=','approved')]", "offset": 0, "limit": 100}
#
    @route(['/mobikul/marketplace/seller/ask'], csrf=False, type='http', auth="none", methods=['POST'])
    def sellerAsk(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            Partner = response.get("context",{}).get("partner")
            if Partner and Partner.seller:
                ask_Query = "<p><b>%s</b></p><p>%s</p>" % (
                    self._mData.get('title') or "", self._mData.get('body'))
                mail_id = Partner.message_post(
                    body=ask_Query, message_type='comment', subtype_xmlid="mail.mt_comment", author_id=response.get('customerId'))
                if mail_id:
                    result = {'message': _('Seller query is posted Successfully'), 'success': True}
                else:
                    result = {'message': 'Something went wrong in posted query', 'success': False}
            else:
                result = {'success': False, 'message': 'Customer is not a seller !!!'}
            response.update(result)
        return self._response('sellerAsk', response)
#
    @route(['/mobikul/marketplace/seller/product'], csrf=False, type='http', auth="none", website=True, methods=['POST'])
    def sellerProduct(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            Partner = response.get("context",{}).get("partner")
            if Partner and Partner.seller:
                TemplateObj = request.env['product.template'].sudo()
                context = response.get('context', {})
                domain = [('marketplace_seller_id', '=', response.get('customerId'))]
                if self._mData.get('state'):
                    domain += [('status', '=', self._mData.get('state'))]
                productDetailsCount = TemplateObj.search_count(domain)
                productDetails = TemplateObj.search(domain, limit=self._mData.get('limit', response.get(
                    'itemsPerPage', 5)), offset=self._mData.get('offset', 0),  order="id desc")
                slr_product = []
                for prd in productDetails:
                    temp = {
                        "name": prd.name,
                        'templateId': prd.id,
                        'state': prd.status,
                        'thumbNail': _get_image_url(self.base_url, 'product.template', prd.id, 'image_1920', prd.write_date),
                        'seller': prd.marketplace_seller_id.name,
                        'qty': prd.qty_available,

                        'priceUnit': _displayWithCurrency(context.get('lang_obj'), prd.list_price, context.get('currencySymbol', ""), context.get('currencyPosition', "")),
                    }
                    slr_product.append(temp)
                result = {'success': True, 'sellerProduct': slr_product,
                          "tcount": productDetailsCount, "offset": self._mData.get('offset', 0)}
            else:
                result = {'success': False, 'message': 'Customer is not a seller !!!'}
            response.update(result)
        return self._response('sellerProduct', response)
#
    @route(['/mobikul/marketplace/seller/dashboard'], csrf=False, type='http', auth="none", methods=['GET'])
    def sellerDashboard(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            context = response.get("context",{})
            Mobikul = context.get('mobikul_obj')
            Partner = context.get("partner")
            if Partner and Partner.seller:
                sellerData = Mobikul.sellerDashboardData(seller_Obj=Partner)
                result = {'success': True, 'sellerDashboard': sellerData}
            else:
                result = {'success': False, 'message': 'Customer is not a seller !!!'}
            response.update(result)
        return self._response('sellerDashboard', response)

    @route(['/mobikul/marketplace/seller/terms'], csrf=False, type='http', auth="public", methods=['GET'])
    def sellerTermCond(self, **kwargs):
        response = self._authenticate(False, **kwargs)
        context = response.get('context')
        website = context.get('websiteObj')
        term_and_condition = website and website.mp_term_and_condition
        if response.get('success'):
            result = {
                "term_and_condition": term_and_condition and remove_htmltags(term_and_condition) or "",
            }
            response.update(result)
        return self._response('sellerTermCond', response)

    @route(['/mobikul/marketplace/become/seller'], csrf=False, type='http', auth="none", website=True, methods=['POST'])
    def becomeSeller(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            context = response.get("context",{})
            Mobikul = context.get('mobikul_obj')
            user = context.get('user').sudo()
            if not user.partner_id.seller:
                if self._mData.get('url_handler') and Mobikul.checkSellerUniqueUrl(self._mData.get('url_handler')):
                    Mobikul.set_marketplace_group_user(user)
                    user.partner_id.seller = True
                    user.partner_id.url_handler = self._mData.get('url_handler')
                    user.partner_id.country_id = self._mData.get('country_id')
                    result = {'success': True, 'message': 'Successfully became a seller'}
                else:
                    result = {'success': False, 'message': _(
                        "Seller profile 'url_handler' is not unique or absent.")}
            else:
                result = {'success': False, 'message': 'Customer is already a seller'}
        response.update(result)
        return self._response('becomeSeller', response)


    @route(['/mobikul/gdpr/deactivate'], csrf=False, type='http', auth="none", methods=['POST'])
    def deactivateAccount(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        result = {}
        if response.get('success'):
            context = response.get("context",{})
            user = context.get('user').sudo()
            if response.get('addons', {}).get('odoo_gdpr'):
                requestObj = request.env['gdpr.request'].sudo()
                if self._mData.get('type') == "temporary":
                    user.active = False
                    result = {'success': True, 'message': 'Your Account is temporary deactivated.'}
                elif self._mData.get('type') == "permanent":
                    requestVals = {
                        "partner_id": user.partner_id.id,
                        "operation_type": "all",
                        "action_type": "delete",
                        "state": "pending"
                    }
                    requestObj.create(requestVals)
                    user.active = False
                    result = {'success': True, 'message': 'Your Account is permananetly deactivated.'}
                else:
                    result = {'success': False,
                              'message': 'Type not found!. Niether permanent nor temporary '}
            else:
                result = {'success': False, 'message': 'Odoo GDPR is not install.'}
        response.update(result)
        return self._response('deactivateAccount', response)
#
    @route(['/mobikul/gdpr/download'], csrf=False, type='http', auth="none", methods=['GET'])
    def downloadAccount(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        result = {}
        if response.get('success'):
            context = response.get("context",{})
            user = context.get('user').sudo()
            if response.get('addons', {}).get('odoo_gdpr'):
                gdprRequest = request.env['gdpr.request'].sudo()
                downloadReq = gdprRequest.search([("partner_id", "=", user.partner_id.id), (
                    "action_type", "=", "download"), ("operation_type", "=", "all")], order="id desc", limit=1)
                if downloadReq:
                    if downloadReq.state == "pending":
                        result = {
                            "downloadRequest": False,
                            "downloadMessage": "We have already received your request, it is in pending state.",
                            "downloadUrl": ""
                        }
                    elif downloadReq.state == "cancel":
                        result = {
                            "downloadRequest": False,
                            "downloadMessage": "Your request is cancel by Admin, for more info contact support.",
                            "state": "cancel",
                            "downloadUrl": ""
                        }
                    elif downloadReq.state == "done":
                        result = {
                            "downloadRequest": False,
                            "state": "done",
                            "downloadMessage": "Your Download is ready, it will expire in 30 days.",
                            "downloadUrl": self.base_url+"web/content/%s?download=true" % downloadReq.attach_id.id
                        }
                    else:
                        result = {
                            "downloadMessage": "Something Went Wrong",
                        }
                else:
                    result = {
                        "downloadRequest": True,
                        "downloadMessage": "",
                        "downloadUrl": ""
                    }
            else:
                result = {'success': False, 'message': 'Odoo GDPR is not install.'}
        response.update(result)
        return self._response('downloadAccount', response)
#
    @route(['/mobikul/gdpr/downloadRequest'], csrf=False, type='http', auth="none", methods=['POST'])
    def downloadRequest(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        result = {}
        if response.get('success'):
            context = response.get("context",{})
            user = context.get('user').sudo()
            if response.get('addons', {}).get('odoo_gdpr'):
                requestObj = request.env['gdpr.request'].sudo()
                if self._checkAlreadyRequest(requestObj, user):
                    result = {'success': False,
                              'message': 'Your download request is already submitted.'}
                else:
                    requestVals = {
                        "partner_id": user.partner_id.id,
                        "operation_type": "all",
                        "action_type": "download",
                        "state": "pending"
                    }
                    requestObj.create(requestVals)
                    result = {'success': True,
                              'message': 'Your download request is submitted successfully.'}
            else:
                result = {'success': False, 'message': 'Odoo GDPR is not install.'}
        response.update(result)
        return self._response('downloadRequest', response)

    @route(['/mobikul/contactUs'],csrf=False,type='http',auth="none",method=['GET'])
    def contactUs(self,**kwargs):
        response = self._authenticate(False,**kwargs)
        result = {}
        if(response.get("success")):
            context = response.get("context",{})
            companyObj = context.get("mobikul_obj").company_id
            result = {
                'companyName':companyObj.name or "",
                'address':str(companyObj.street)+"\n"+str(companyObj.city)+"\n"+str(companyObj.state_id.name)+"\n"+str(companyObj.zip)+"\n"+str(companyObj.country_id.name) or "",
                'phone':companyObj.phone or "",
                'email':companyObj.email or ""
            }
        response.update(result)
        return self._response('contactUs',response)

    @route(['/mobikul/walkThrough'],csrf=False,type='http',auth="none",method=['GET'])
    def walkThrough(self,**kwargs):
        response = self._authenticate(False,**kwargs)
        result = []
        if response.get("success"):
            allow_walkThrough = literal_eval(request.env['ir.config_parameter'].sudo().get_param('mobikul.walk_through', 'False'))
            mobikulObj = response.get("context").get("mobikul_obj")
            if allow_walkThrough:
                for walkthrough in mobikulObj.walk_through_ids:
                    if walkthrough.status == 'enable':
                        temp = {
                            "title": walkthrough.name,
                            "description": walkthrough.description or "",
                            "sequence": walkthrough.sequence,
                            "colorCode": walkthrough.color_code or "",
                            "image": mobikulObj._get_image_url('mobikul.walkthrough', walkthrough.id, 'image', walkthrough.write_date,context=response.get("context")),
                        }
                        result.append(temp)
            result = sorted(result, key=lambda d: d['sequence'])
        response.update({"walkThroughData":result})
        return self._response('walkThrough',response)

    @route(['/mobikul/addToCompare'],csrf=False,type='http',auth="public",website=True,method=['GET'])
    def addToCompare(self,**kwargs):
        response = self._authenticate(False,**kwargs)
        product_ids = literal_eval(kwargs.get('products')) if kwargs.get('products') else []
        if response.get("success"):
            if response.get('addons', {}).get('website_sale_comparison'):
                product_ids = request.env["product.product"].sudo().browse(product_ids)
                data = product_ids._prepare_categories_for_display()
                result = self._get_compare_product_data(data,product_ids,context=response.get("context"))
            else:
                result = {'success': False, 'message': 'Product Comparison Module is not installed.'}
        response.update(result)
        return self._response('addToCompare',response)

    @route('/mobikul/mergeCart', csrf=False, type='http', auth="none",website=True, methods=['POST'])
    def mergeCart(self, **kwargs):
        response = self._authenticate(True, **kwargs)
        if response.get('success'):
            context = response.get('context')
            guestOrder = context.get('tokenObj').last_guest_so_id or False
            if guestOrder:
                Partner = context.get('partner').sudo()
                Partner.last_mobikul_so_id = guestOrder.id
                Partner.last_mobikul_so_id.partner_id = Partner.id
                Partner.with_context(context).sudo().last_website_so_id = guestOrder.id
                context.get('tokenObj').last_guest_so_id = False
                response['message'] = 'Cart merged successfully.'
            else:
                response['message'] = 'Guest user have no order yet.'
        return self._response('mergeCart', response)


    def _get_product_data(self,products,context):
        base_url = context.get("base_url")
        pricelist = context.get("pricelist", False)
        lang_obj = context.get("lang_obj")
        currency_symbol = context.get("currencySymbol")
        currency_position = context.get("currencyPosition")
        product_list = []
        for product in products:
            comb_info = product_temp.with_context(context)._get_combination_info(combination=False, product_id=False,add_qty=1, pricelist=pricelist, parent_combination=False, only_template=False)
            temp = {"id":product.id,"templateId":product_temp.id,"productVarientCount":product.product_variant_count,"name":product.name,
                    "priceUnit":_displayWithCurrency(lang_obj,comb_info['has_discounted_price'] and comb_info['list_price'] or comb_info['price'] or 0, currency_symbol, currency_position),
            "thumbNail":_get_image_url(base_url, 'product.product', product.id, 'image_1920', product.write_date)}
            product_list.append(temp)
        return product_list

    def _get_product_attribute_data(self,data):
        show_category = False
        attributeValueList = []
        for category in data:
            temp = {"title":"","attributeList":[]}
            if category.name and not show_category:
                show_category = True
            temp.update({"title":category.name or show_category and _("Uncategorized") or ""})
            for attr in data[category]:
                temp1 = {"attributeName":attr.name,"value":[]}
                for product in data[category][attr]:
                    if data[category][attr][product]:
                        for ptav in data[category][attr][product]:
                            temp1['value'].append(ptav.name)
                    else:
                         temp1['value'].append("")
                temp['attributeList'].append(temp1)
            attributeValueList.append(temp)
        return attributeValueList,show_category



    def _get_compare_product_data(self,data,products,context):
        result = {"productsList":[],"attributeValueList":[]}
        product_data = self._get_product_data(products,context=context)
        attribute_data,show_category = self._get_product_attribute_data(data)
        result.update({"showTitle":show_category,"productsList":product_data,"attributeValueList":attribute_data})
        return result


    def _checkAlreadyRequest(self, requestObj, user):
        domain = [
            ("partner_id", "=", user.partner_id.id),
            ("operation_type", "=", "all"),
            ("action_type", "=", "download"),
            ("state", "=", "pending"),
        ]
        req = requestObj.search(domain)
        return req and True or False

    def _removeAddress(self,partner):
        for address in partner.child_ids:
            # if address.type == "delivery":
            address.write(self.anonymize_details())

    def anonymize_details(self,user=False,s_login=False):
        vals={}
      	# ANONYMIZED_DETAILS
        rand_no = fields.datetime.now().strftime('%Y-%m-%d-%H:%M:%S').replace(" ", "")
        rand_mob = 'UserMob@' + rand_no
        vals.update({"phone":rand_mob })
        if s_login:
            for field in ANONYMIZED_DETAILS.get("user").get("user_social_login_fields"):
                vals.update({field : "N/A"})
            vals.update({"oauth_provider_id":False })
        if user:
            for field in ANONYMIZED_DETAILS.get("user").get("user_fields"):
                vals.update({ field : "N/A"})

        for field in ANONYMIZED_DETAILS.get("partner").get("partner_fields"):
            vals.update({field : "N/A"})
        for field in ANONYMIZED_DETAILS.get("partner").get("partner_related_fields"):
            vals.update({field : False})
        return vals

from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
	
class DBPortalAccount(CustomerPortal):
	@route(['/mobikul/invoices/<int:invoice_id>'], type='http', auth="public", website=True,method=["GET"])
	def mobikul_invoice_detail(self, invoice_id, access_token=None, report_type=None, download=False, **kw):
		model_id = request.env["account.move"].sudo().browse(invoice_id)
		if report_type in ('html', 'pdf', 'text'):
			return self._show_report(model=model_id, report_type=report_type, report_ref='account.account_invoices', download=download)

		values = self._invoice_get_page_view_values(model_id, access_token, **kw)
		return request.render("account.portal_invoice_page", values)


from odoo import http

class ProductAPI(http.Controller):
    @http.route('/mobkul/products/search-variant', type='json', auth='none', methods=['POST'], csrf=False)
    def get_products_by_variant(self, **kwargs):
        """
        API to get products by variant value.
        :param search_bar: Dictionary with variant keys and values to filter products.
        :return: JSON response with products.
        """
        try:
            search_bar = kwargs.get('search_bar')
            if not search_bar or not isinstance(search_bar, dict):
                return {"error": "Invalid or missing 'search_bar' parameter. It must be a dictionary."}
            keys_list = list(search_bar.keys())
            values_list = list(search_bar.values())
            values_list = [value.lower() if isinstance(value, str) else value for value in values_list]
            variant_attribute = request.env['product.attribute'].sudo().search([
                ('name', 'in', keys_list),
            ])
            if not variant_attribute:
                return {"error": "Variant not found."}
            domain = ['&',('attribute_id', 'in', variant_attribute.ids)]
            i = 1
            for value in values_list:
                domain.append(('name', 'ilike', value))
                if i != 1:
                    domain.insert(1,'|')
                i += 1
            attribute_id = request.env['product.attribute.value'].sudo().search(domain)
            products = request.env['product.template.attribute.line'].sudo().search(
                [('value_ids', 'in', attribute_id.ids)])
            product_data = []
            for product in products:
                product_temp = product.product_tmpl_id
                for pro in product_temp.product_variant_ids:
                    print(pro)
                    product_value = []
                    for value in pro.product_template_attribute_value_ids:
                        product_value.append(value.name.lower())
                    _logger.info("Comparsion List %s,,,,%s",product_value,values_list)
                    if all(val in product_value for val in values_list):
                        product_data.append([{
                        "templateId": product_temp.id,
                        'productId': pro.id,
                        'name': product_temp.name,
                        'priceReduce': "",
                        'default_code': pro.default_code,
                        'priceUnit': product_temp.list_price,
                        'productId': product_temp.product_variant_id and product_temp.product_variant_id.id or '',
                        'productCount': product_temp.product_variant_count or 0,
                        'description': product_temp.description_sale or '',
                        'thumbNail': '%sweb/image/%s/%s/%s?unique=%s' % ('https://bazar-iq.filesdna.com/', 'product.template', product_temp.id, 'image_1920', re.sub('[^\d]', '', fields.Datetime.to_string(product_temp.write_date))),
                        'ribbon': {
                                        'ribbon_message': product_temp.website_ribbon_id.html or '',
                                        'position': product_temp.website_ribbon_id.html_class or '',
                                        'text_color': product_temp.website_ribbon_id.text_color or '#589ff5',
                                        'bg_color':  product_temp.website_ribbon_id.bg_color or '#f7f9fa'
                                    }
                        }])


            return {"success": True, "products": product_data}

        except Exception as e:
            return {"error": str(e)}

    @http.route('/mobkul/variants', type='json', auth='none', methods=['GET'], csrf=False)
    def get_product_variants(self):
        """
        API to retrieve product variants and their attribute values in the format:
        {'Brand': ['HP', 'Samsung'], 'Size': ['Small', 'Medium']}
        """
        try:
            # Fetch all product variants and their attribute values
            product_attribute_lines = request.env['product.template.attribute.line'].sudo().search([])
            
            # Initialize the result dictionary
            variant_data = {}

            for line in product_attribute_lines:
                attribute_name = line.attribute_id.name
                # Get the values for this attribute
                values = [value.name for value in line.value_ids]
                if attribute_name in variant_data:
                    variant_data[attribute_name].extend(values)
                else:
                    variant_data[attribute_name] = values
            
            # Remove duplicates
            for key in variant_data:
                variant_data[key] = list(set(variant_data[key]))

            return {'success':True, 'data': variant_data}

        except Exception as e:
            return {'success': False, 'message': str(e)}