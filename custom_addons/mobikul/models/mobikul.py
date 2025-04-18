# -*- coding: utf-8 -*-
##########################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
##########################################################################
from odoo.addons.mobikul.tool.help import _displayWithCurrency, _default_unique_key, _get_image_url, _getProductData, _get_product_domain, _get_product_fields, _easy_date
from ast import literal_eval
from odoo.http import request
from odoo import api, fields, models, _, SUPERUSER_ID
from datetime import datetime
from odoo.exceptions import UserError
import random
import uuid
import json
import base64
import re
import os
from odoo.addons.mobikul.tool.fcmAPI import FCMAPI
from odoo.addons.base.models.ir_mail_server import MailDeliveryException
import logging
_logger = logging.getLogger(__name__)


class Mobikul(models.Model):
    _name = "mobikul"
    _description = "Mobikul Model"

    @api.model
    def _create_so(self, partner, context):
        result = {"success": True}
        addr = partner.address_get(['delivery'])
        so_data = {
            'partner_id': partner.id,
            'pricelist_id': context.get('pricelist').id,
            'payment_term_id': partner.property_payment_term_id.id,
            'team_id': context.get("teamId"),
            'partner_invoice_id': partner.id,
            'partner_shipping_id': addr['delivery'],
            'user_id': context.get("salespersonId"),
            'website_id': context.get("website_id")
        }

        company = context.get("pricelist").company_id
        if company:
            so_data['company_id'] = company.id
        # Create sale order with the current authorized user partner
        result['order'] = partner.env['sale.order'].sudo().create(so_data)

        if context.get('is_guest'):
            context.get('tokenObj').last_guest_so_id = result['order'].id
        else:
            partner.sudo().write({'last_mobikul_so_id': result['order'].id})
        result['cartId'] = result['order'].id
        return result

    def _lang_get(cls):
        _logger.info("===========cls==%r",cls)
        return cls.env['res.lang'].get_installed()

    @api.model
    def _validate(self, api_key, context=None):
        context = context or {}
        response = {'success': False, 'responseCode': 0, 'message': _('Unknown Error !!!')}
        if not api_key:
            response['message'] = _('Invalid/Missing Api Key !!!')
            return response
        try:
            mobikul = context.get("mobikul_obj") or self.env['mobikul'].sudo().search([], limit=1)
            if not mobikul:
                response['responseCode'] = 1
                response['message'] = _("Mobikul Configuration not found !!!")
            elif mobikul.api_key != api_key:
                response['responseCode'] = 1
                response['message'] = _("API Key is invalid !!!")
            else:
                token = context.get('fcmToken')
                tokenObj = self.env['fcm.registered.devices'].sudo().search([('token','=',token)],limit=1)
                app_lang = context.get(
                    'lang') or mobikul.default_lang and mobikul.default_lang.code or "en_US"
                tz = context.get('tz')
                pricelist_id = context.get('pricelist', False) or mobikul.pricelist_id.id
                app_pricelist = self.env['product.pricelist'].sudo().browse(int(pricelist_id))
                response["itemsPerPage"] = mobikul.product_limit
                response['success'] = True
                response['responseCode'] = 2
                response['message'] = _('Login successfully.')
                response["context"] = {
                    "pricelist": app_pricelist,
                    "currency_id": app_pricelist.currency_id,
                    'currencySymbol': app_pricelist.currency_id.symbol or "",
                    'currencyPosition': app_pricelist.currency_id.position or "",
                    'allowed_company_ids': [mobikul.company_id.id],
                    'website_id': mobikul.website_id.id,
                    'websiteObj': mobikul.website_id,
                    'tz': tz,
                    'bin_size': False,
                    'edit_translations': False,
                    'uid': self.env.ref('base.public_user', False) and self.env.ref('base.public_user').id,
                    'partner': self.env.ref('base.public_partner', False),
                    "user": self.env.ref('base.public_user', False),
                    'lang': app_lang,
                    'teamId': mobikul.salesteam_id and mobikul.salesteam_id.id or False,
                    'salespersonId': mobikul.salesperson_id and mobikul.salesperson_id.id or False,
                    'lang_obj': self.env['res.lang']._lang_get(app_lang),
                    "base_url": context.get("base_url"),
                    "sync_order": context.get("sync_order"),
                    "tokenObj":tokenObj,
                    "is_guest":context.get("is_guest")
                }
                response['context']["mobikul_obj"] = mobikul.with_context(response['context'])
                response['addons'] = self.check_mobikul_addons()
        except Exception as e:
            response['responseCode'] = 3
            response['message'] = _("Login Failed:")+"%r" % e
        return response

    @api.model
    def _get_image_url(self, model_name, record_id, field_name, write_date=0, width=0, height=0, context=None):
        """ Returns a local url that points to the image field of a given browse record. """
        context = context or {}
        if context.get('base_url', "") and not context['base_url'].endswith("/"):
            context['base_url'] = context['base_url'] + "/"
        if width or height:
            return '%sweb/image/%s/%s/%s/%sx%s?unique=%s' % (context.get('base_url'), model_name, record_id, field_name, width, height, re.sub('[^\d]', '', fields.Datetime.to_string(write_date)))
        else:
            return '%sweb/image/%s/%s/%s?unique=%s' % (context.get('base_url'), model_name, record_id, field_name, re.sub('[^\d]', '', fields.Datetime.to_string(write_date)))

    @api.model
    def _get_cat_info(self, categ_obj, context=None):
        context = context or {}
        cat_data = {
            "category_id": categ_obj.id,
            "name": categ_obj.name or "",
            "children": [],
            "icon": self._get_image_url('mobikul.category', categ_obj.id, 'icon', categ_obj.write_date, context=context),
        }
        return cat_data

    @api.model
    def _recursive_cats(self, categ_obj, context=None):
        context = context or {}
        data = self._get_cat_info(categ_obj, context)
        if categ_obj.child_id:
            for cat_child in categ_obj.child_id:
                data['children'].append(self._recursive_cats(cat_child, context))
        return data

    @api.model
    def fetch_categories(self, context=None):
        context = context or {}
        all_cats = []
        if context.get('website_category', False):
            return all_cats
        else:
            cat_obj = self.env['mobikul.category'].sudo()
        top_cats = cat_obj.search([('parent_id', '=', False)])
        for top_cat in top_cats:
            all_cats.append(self._recursive_cats(top_cat, context))
        return all_cats

    @api.model
    def fetch_featured_categories(self,mobikulhomepageObj, context=None):
        context = context or {}
        all_fcats = []
        if context.get('website_category', False):
            return all_fcats
        else:
            cat_obj = self.env['mobikul.category'].sudo()
        f_cats = cat_obj.search([('id','in',mobikulhomepageObj.featured_category_ids.ids)])

        for f_cat in f_cats:
            temp_f = {
                'categoryName': f_cat.name or "",
                'categoryId': f_cat.id
            }
            temp_f['url'] = self._get_image_url(
                'mobikul.category', f_cat.id, 'icon', f_cat.write_date, context=context)
            all_fcats.append(temp_f)
        return all_fcats

    @api.model
    def fetch_product_sliders(self,mobikulhomepageObj, context=None):
        context = context or {}
        allProductSliders = []
        pSlider_obj = self.env['mobikul.product.slider'].sudo()
        p_sliders = pSlider_obj.search([('id','in',mobikulhomepageObj.slider_ids.ids)])
        for p_slider in p_sliders:

            products = p_slider.get_product_data(context)['products']
            if not len(products):
                continue
            temp_s = {
                'title': p_slider.name or "",
                'item_display_limit': p_slider.item_display_limit,
                'slider_mode': p_slider.slider_mode or "",
                'products': products,
                'url': "/mobikul/sliderProducts/%d" % p_slider.id,
            }
            if p_slider.display_banner:
                temp_s['backImage'] = self._get_image_url(
                    'mobikul.product.slider', p_slider.id, 'banner', p_slider.write_date, context=context)
            allProductSliders.append(temp_s)
        return allProductSliders

    @api.model
    def fetch_user_info(self, user_obj, context=None):
        context = context or {}
        temp_i = {
            'customerBannerImage': self._get_image_url('res.partner', user_obj.partner_id.id, 'banner_image', user_obj.partner_id.write_date, context=context),
            'customerProfileImage': self._get_image_url('res.partner', user_obj.partner_id.id, 'image_1920', user_obj.partner_id.write_date, context=context),
            'cartId': user_obj.partner_id.last_mobikul_so_id and user_obj.partner_id.last_mobikul_so_id.id or '',
            'themeCode': '?',
            'customerName': user_obj.partner_id.name or "",
            'customerEmail': user_obj.login or "",
            'customerLang': user_obj.partner_id.lang.split('_')[0],
        }
        return temp_i

    @api.model
    def authenticate(self, credentials, detailed=False, isSocialLogin=False, context=None):
        context = context or {}
        response = {'success': False, 'responseCode': 0, 'message': _('Unknown Error !!!')}
        guestUser = False
        user = False
        if not isinstance(credentials, dict) and not context.get("is_guest"):
            response['message'] = _('Data is not in Dictionary format !!!')
            return response
        if isSocialLogin:
            if not all(k in credentials for k in ('authProvider', 'authUserId')):
                response['message'] = _('Insufficient data to authenticate !!!')
                return response
            provider = self._getAuthProvider(credentials['authProvider'])
            try:
                user = self.env['res.users'].sudo().search(
                    [('oauth_uid', '=', credentials['authUserId']), ('oauth_provider_id', '=', provider)])
                if not user:
                    response['responseCode'] = 1
                    response['message'] = _("Social-Login: No such record found.")
            except Exception as e:
                response['responseCode'] = 3
                response['message'] = _("Social-Login Failed.")
                response['details'] = "%r" % e
        else:
            if context.get("is_guest"):
                guestUser = True
            else:
                if not all(k in credentials for k in ('login', 'pwd')):
                    response['message'] = _('Insufficient data to authenticate !!!')
                    return response
                try:
                    user = self.env['res.users'].sudo().search([('login', '=', credentials['login'])])
                    if user:
                        user.with_user(user)._check_credentials(credentials['pwd'],{'interactive':True})
                    else:
                        response['responseCode'] = 1
                        response['message'] = _("Invalid email address.")
                        response['accessDenied'] = True
                except Exception as e:
                    user = False
                    response['responseCode'] = 3
                    response['message'] = _("Login Failed.")
                    response['details'] = "%r" % e
                    response['accessDenied'] = True

        if user:
            # Remove the superuser privilege and assign the respective user rights
            user = user.with_user(user)
            Partner = user.partner_id.sudo()
            if Partner:
                if Partner.property_product_pricelist.id != context.get("pricelist").id:
                    Partner.property_product_pricelist = context.get("pricelist").id
                last_order = Partner.last_mobikul_so_id
                if last_order.state in ['sale','done','sent','cancel']:
                    Partner.last_mobikul_so_id = False
                if context.get("sync_order"):
                    if (not Partner.last_mobikul_so_id):
                        self._sync_lastOrder(Partner)


            try:
                response['success'] = True
                response['responseCode'] = 2
                response['customerId'] = Partner.id
                response['userId'] = user.id
                response['cartCount'] = Partner.last_mobikul_so_id and Partner.last_mobikul_so_id.cart_count or 0
                response['message'] = _('Login successfully.')
                context.update({"partner": Partner, "uid": user.id,
                                "user": user, "order":Partner.last_mobikul_so_id,'tz':context.get('tz') or user.tz})
                if self.check_mobikul_addons().get('wishlist'):
                    response['WishlistCount'] = len(Partner.wishlist_ids)
                if self.check_mobikul_addons().get('email_verification'):
                    response['is_email_verified'] = user.wk_token_verified
                if self.check_mobikul_addons().get('odoo_marketplace'):
                    response['is_seller_requested'] = True if Partner.seller else False
                    response['is_seller'] = Partner.seller and Partner.state == 'approved'
                    if Partner.seller:
                        response['seller_group'] = self.check_seller_state(user)
                        response['seller_state'] = Partner.state
                if detailed:
                    response.update(self.fetch_user_info(user, context=context))
            except Exception as e:
                response['responseCode'] = 3
                response['message'] = _("Login Failed.")
                response['details'] = "%r" % e

        if guestUser:
            guestOrder = context.get('tokenObj').last_guest_so_id
            if guestOrder.state in ['sale','done','sent','cancel']:
                    context.get('tokenObj').last_guest_so_id = False
            IrConfigParam = self.env['ir.config_parameter']
            allow_guestCheckout = literal_eval(IrConfigParam.get_param('mobikul.guest_checkout', 'False'))
            if allow_guestCheckout:
                response['success'] = True
                response['responseCode'] = 2
                response['cartCount'] = context.get('tokenObj') and context.get('tokenObj').last_guest_so_id.cart_count or 0
                response['message'] = _('Welcome Guest user')
                context.update({"order": guestOrder})
            else:
                response['success'] = False
                response['responseCode'] = 4
                response['message'] = _('Guest checkout setting is not enabled')
        response["context"] = context
        return response

    def _sync_lastOrder(self,Partner):
        order = self.env["sale.order"].sudo().search([
                    ('partner_id', '=', Partner.id),
                    ('website_id', '=', self._context.get("websiteObj").id),
                    ('state', '=', 'draft'),
                ], order='write_date desc', limit=1)
        Partner.last_mobikul_so_id = order
        return True


    def check_seller_state(self, user):
        user_groupObj = self.env['ir.model.data'].sudo()
        user_group_ids = user.groups_id.ids
        xml_ids = ["marketplace_seller_group",
                   "marketplace_officer_group", "marketplace_manager_group"]
        for xml_id in xml_ids:
            mp_group = user_groupObj.check_object_reference('odoo_marketplace', xml_id)[
                1] in user_group_ids and xml_id or ""
            break
        return mp_group

    def check_mobikul_addons(self):
        result = {}
        ir_model_obj = self.env['ir.module.module'].sudo()
        result['wishlist'] = ir_model_obj.search(
            [('state', '=', 'installed'), ('name', '=', 'website_sale_wishlist')]) and True or False
        result['review'] = ir_model_obj.search(
            [('state', '=', 'installed'), ('name', '=', 'wk_review')]) and True or False
        result['email_verification'] = ir_model_obj.search(
            [('state', '=', 'installed'), ('name', '=', 'email_verification')]) and True or False
        result['odoo_marketplace'] = ir_model_obj.search(
            [('state', '=', 'installed'), ('name', '=', 'odoo_marketplace')]) and True or False
        result['delivery'] = ir_model_obj.search(
            [('state', '=', 'installed'), ('name', '=', 'delivery')]) and True or False
        result['odoo_gdpr'] = ir_model_obj.search(
            [('state', '=', 'installed'), ('name', '=', 'odoo_gdpr')]) and True or False
        result['website_sale_stock'] = ir_model_obj.search(
            [('state', '=', 'installed'), ('name', '=', 'website_sale_stock')]) and True or False
        result['website_sale_comparison'] = ir_model_obj.search(
            [('state', '=', 'installed'), ('name', '=', 'website_sale_comparison')]) and True or False
        result['delivery_boy'] = ir_model_obj.search(
            [('state', '=', 'installed'), ('name', '=', 'delivery_boy')]) and True or False
        return result

    def email_verification_defaults(self):
        return self.env['email.verification.config'].sudo().get_values()

    def review_defaults(self):
        return self.env['website.review.config'].sudo().get_values()

    def fecth_data(self, mobikulhomepageObj, context=None):
        if mobikulhomepageObj.type == "banner":
            return self.fetch_banners(mobikulhomepageObj, context=context)
        elif mobikulhomepageObj.type == "slider":
            return self.fetch_product_sliders(mobikulhomepageObj, context=context)
        elif mobikulhomepageObj.type == "featured_category":
            return self.fetch_featured_categories(mobikulhomepageObj, context=context)
            
    
    def get_homepage_data(self, homepage_id, context=None, **kwargs):
        context = context or {}
        hdatalst = []
        homepageDatas = homepage_id.homepage_ids[int(kwargs.get('offset',0)):int(kwargs.get('offset',0))+5]
        for hData in homepageDatas:
            data = {
                'name': hData.name,
                'type': hData.type,
                'data': self.fecth_data(hData,context=context)
            }
            if hData.type == "featured_category":
                data['featured_category_view_type'] = hData.featured_category_view
            hdatalst.append(data)

        return hdatalst

    @api.model
    def homePage(self, cust_data, context, **kwargs):
        context = context or {}
        response = {}
        # Get base url
        # if not context.has_key("base_url"):
        if not 'base_url' in context:
            context['base_url'] = self.env['ir.config_parameter'].get_param('web.base.url')
        # Get Mobikul Conf
        mobikul = context.get('mobikul_obj') or self.env['mobikul'].sudo().search([], limit=1)
        # Get all Categories
        response['categories'] = self.fetch_categories(context=context)
        # Get Mobikul Homepage Data
        response['homepageDataCount'] = mobikul and mobikul.homepage_id and len(mobikul.homepage_id.homepage_ids) or 0
        response['homepageData'] = mobikul and mobikul.homepage_id and self.get_homepage_data(mobikul.homepage_id, context=context, **kwargs) or []
        return response

    @api.model
    def fetch_countries(self):
        try:
            self.ensure_one()
        except ValueError:
            self = self.search([], limit=1)
        domain = []
        if self.country_ids:
            domain = [("id", "in", [c.id for c in self.country_ids])]
        countries = self.env['res.country'].sudo().search_read(domain, fields=['name', 'state_ids'])
        return countries

    @api.model
    def fetch_banners(self, mobikulhomepageObj, context=None):
        context = context or {}
        all_banners = []
        MobBanners = self.env['mobikul.banners'].sudo().search_read([('id','in',mobikulhomepageObj.banner_ids.ids)])
        for banner in MobBanners:
            temp_d = {
                "bannerName": banner['name'],
                "bannerType": banner['banner_action'],
                "id": '',
            }
            if banner['banner_action'] == "product":
                temp_d['id'] = banner["product_id"][0]
            elif banner['banner_action'] == "category":
                temp_d['id'] = banner["category_id"][0]
            elif banner['banner_action'] == "custom":
                temp_d['domain'] = "[('id','in',%r)]" % banner["product_ids"]
            if banner['image']:
                temp_d['url'] = self._get_image_url(
                    'mobikul.banners', banner['id'], 'image', banner['write_date'], context=context)
            else:
                temp_d['url'] = banner['url']
            all_banners.append(temp_d)
        return all_banners

    @api.model
    def resetPassword(self, login):
        response = {'success': False}
        try:
            if login:
                self.env['res.users'].sudo().reset_password(login)
                response['success'] = True
                response['message'] = _(
                    "An email has been sent with credentials to reset your password")
            else:
                response['message'] = _("No login provided.")
        except MailDeliveryException as me:
            response['message'] = _("Exception : %r" % me)
        except Exception as e:
            response['message'] = _("Invalid Username/Email.")
        return response

    @api.model
    def _getAuthProvider(self, provider):
        provider_id = self.env['auth.oauth.provider'].sudo()
        if provider == "GMAIL":
            google_provider = self.env.ref('auth_oauth.provider_google') or provider_id.search([('mobikul_oauth_ref_code','=','GMAIL')])
            return google_provider and google_provider.id or False
        elif provider == "FACEBOOK":
            facebook_provider = self.env.ref('auth_oauth.provider_facebook') or provider_id.search([('mobikul_oauth_ref_code','=','FACEBOOK')])
            return facebook_provider and facebook_provider.id or False
        elif provider == "TWITTER":
            twitter_provider = provider_id.search([('mobikul_oauth_ref_code','=','TWITTER')])
            return twitter_provider and twitter_provider.id or False
        elif provider == "INSTAGRAM":
            insta_provider = provider_id.search([('mobikul_oauth_ref_code','=','INSTAGRAM')])
            return insta_provider and insta_provider.id or False
        elif provider == "APPLEID":
            appleId_provider = provider_id.search([('mobikul_oauth_ref_code','=','APPLEID')])
            return appleId_provider and appleId_provider.id or False
        return False

    # def _getAuthProvider(self, provider):
    #     if provider == "GMAIL":
    #         google_provider = self.env.ref('auth_oauth.provider_google')
    #         return google_provider and google_provider.id or False
    #     elif provider == "FACEBOOK":
    #         facebook_provider = self.env.ref('auth_oauth.provider_facebook')
    #         return facebook_provider and facebook_provider.id or False
    #     elif provider == "TWITTER":
    #         twitter_provider = self.env.ref('auth_oauth.provider_twitter')
    #         return twitter_provider and twitter_provider.id or False
    #     return False

    @api.model
    def _doSignup(self, data):
        template_user_id = literal_eval(self.env['ir.config_parameter'].get_param(
            'base.template_portal_user_id', 'False'))
        template_user = self.env['res.users'].browse(template_user_id)
        if not template_user.exists():
            return [False, 'Invalid template user']

        values = {key: data.get(key) for key in ('login', 'name')}
        values['email'] = data.get('email') or values.get('login')
        values['active'] = True
        no_invitation_mail = True
        if data.get('isSocialLogin', False):
            values['oauth_uid'] = data.get('authUserId', "")
            values['oauth_access_token'] = data.get('authToken', "")
            values['oauth_provider_id'] = self._getAuthProvider(data.get('authProvider', ""))
            values['email'] = values.get('email', 'provider_%s_user_%s' %
                                         (values['oauth_provider_id'], values['oauth_uid']))
            values['password'] = data.get("password", values['oauth_uid'])
            if self.check_mobikul_addons().get('email_verification'):
                values['wk_token_verified'] = True
            if not values['oauth_uid'] or not values['oauth_provider_id'] or not values['name'] or not values['email']:
                return [False, "Insufficient data to authenticate."]
        else:
            values['password'] = data.get('password', "")
            no_invitation_mail = values['password'] and True or False
            if not values['name'] or not values['email']:
                return [False, "Insufficient data to authenticate."]
        try:
            if self.check_mobikul_addons().get('email_verification'):
                values["signup_from_website"] = True
            with self.env.cr.savepoint():
                if self.check_mobikul_addons().get('odoo_marketplace') and data.get('is_seller'):
                    seller_msg = self.isMarketplaceSignup(template_user, values, data)
                    if seller_msg.get('status'):
                        return [True, seller_msg.get('user').id, seller_msg.get('user').partner_id.id, seller_msg.get('msg')]
                    else:
                        return [False, _("Seller profile 'url_handler' is not unique or absent.")]
                else:
                    user = template_user.with_context(
                        no_reset_password=no_invitation_mail).copy(values)
                    return [True, user.id, user.partner_id.id, " "]
        except UserError as e:
            return [False, str(e)]
        except Exception as e:
            # copy may failed if asked login is not available.
            # return [False,"Error: %r"%e]
            return [False, _("There is some problem in creating account. Please try again later.")]
        return [False, "Unknown Error"]

    def isMarketplaceSignup(self, template_user, values, data):
        if data.get('url_handler') and self.checkSellerUniqueUrl(data.get('url_handler')):
            user = template_user.with_context(no_reset_password=True).copy(values)
            if user:
                self.set_marketplace_group_user(user)
                # user.partner_id.country = "India"
                user.partner_id.seller = True
                user.partner_id.url_handler = data.get('url_handler')
                user.partner_id.country_id = int(data.get('country_id'))
                return {'status': True, 'msg': _("Seller created successfully"), 'user': user}
            else:
                {"status": False, "msg": _("Something went wrong please try again.")}
        else:
            return {"status": False, "msg": _("Seller profile 'url_handler' is not unique or absent.")}

    def set_marketplace_group_user(self, userObj):

        user_group_id = self.env['ir.model.data'].check_object_reference('base', 'group_portal')[1]
        groups_obj = self.env["res.groups"].browse(user_group_id)
        if groups_obj:
            for group_obj in groups_obj:
                group_obj.write({"users": [(3, userObj.id, 0)]})

        user_group_id = self.env['ir.model.data'].check_object_reference('base', 'group_user')[1]
        groups_obj = self.env["res.groups"].browse(user_group_id)
        if groups_obj:
            for group_obj in groups_obj:
                group_obj.write({"users": [(4, userObj.id, 0)]})

        user_group_id = self.env['ir.model.data'].check_object_reference(
            'odoo_marketplace', 'marketplace_draft_seller_group')[1]
        groups_obj = self.env["res.groups"].browse(user_group_id)
        if groups_obj:
            for group_obj in groups_obj:
                group_obj.write({"users": [(4, userObj.id, 0)]})
                return True
        else:
            return False

    def checkSellerUniqueUrl(self, url):
        if url:
            if not re.match('^[a-zA-Z0-9-_]+$', url) or re.match('^[-_][a-zA-Z0-9-_]*$', url) or re.match('^[a-zA-Z0-9-_]*[-_]$', url):
                raise UserError(
                    _("Only alphanumeric([0-9],[a-z]) and some special characters(-,_) are allowed, Spaces are not allowed."))
            check_url_existObj = self.env['res.partner'].sudo().search(
                [('url_handler', '=', url)], limit=1)
            if len(check_url_existObj) == 0:
                return True
            else:
                return False
        else:
            return False

    @api.model
    def signUp(self, form_data):
        response = {'success': False}
        # MobikulConfigParam = self.search_read([], limit=1)[0]
        # if MobikulConfigParam['signup_enabled']:

        try:
            if form_data.get('isSocialLogin', False):
                provider = self._getAuthProvider(form_data['authProvider'])
                social_user_login = self.env['res.users'].sudo().search(
                    [('oauth_uid', '=', form_data['authUserId']), ('oauth_provider_id', '=', provider)])
                login = self.env['res.users'].sudo().search([("login", "=", form_data['login'])])
                if social_user_login or login:
                    if not social_user_login:
                        data = login.sudo().write({'oauth_uid': form_data['authUserId'],'oauth_provider_id': provider})
                    user = social_user_login.with_user(login)
                    response['success'] = True
                    response['message'] = _("Login Successfully.")
                    response['userId'] = login.id
                    response['customerId'] = login.partner_id.id
                    return response
            if 'login' in form_data:
                if self.env['res.users'].sudo().search([("login", "=", form_data['login'])]):
                    response['message'] = _("This mail is already registered with us. ")

                else:
                    result = self._doSignup(form_data)
                    if result[0]:
                        response['success'] = True
                        response['message'] = _("Created Successfully.")
                        response['createNotification'] = True
                        response['userId'] = result[1]
                        response['customerId'] = result[2]
                        response['seller_message'] = result[3]
                    else:
                        response['message'] = _("Could not create a new account: ")+"%s" % result[1]
            else:
                response['message'] = _("No login provided.")
        except Exception as e:
            response['message'] = _("Could not create a new account.:")+" %r" % e
        return response

    @api.model
    def getDefaultData(self):
        IrConfigParam = self.env['ir.config_parameter']
        temp = {}
        temp['allow_resetPwd'] = literal_eval(
            IrConfigParam.get_param('auth_signup.reset_password', 'False'))
        temp['allow_signup'] = literal_eval(
            IrConfigParam.get_param('auth_signup.allow_uninvited', 'False'))
        temp['allow_guestCheckout'] = literal_eval(
            IrConfigParam.get_param('mobikul.allow_guest', 'False'))
        temp['allow_gmailSign'] = literal_eval(
            IrConfigParam.get_param('mobikul.gmail_signin', 'False'))
        temp['allow_facebookSign'] = literal_eval(
            IrConfigParam.get_param('mobikul.facebook_signin', 'False'))
        temp['allow_twitterSign'] = literal_eval(
            IrConfigParam.get_param('mobikul.twitter_signin', 'False'))
        data = self.check_mobikul_addons()
        temp['allowShipping'] = data.get("delivery")
        temp['privacy_policy_url'] = self.privacy_policy
        allow_walkThrough = literal_eval(IrConfigParam.get_param('mobikul.walk_through', 'False'))
        temp['allow_walkThrough'] = allow_walkThrough
        temp['walkThrough_version'] = allow_walkThrough and literal_eval(IrConfigParam.get_param('mobikul.walk_through_version')) or ""
        temp['allow_guestCheckout'] = literal_eval(IrConfigParam.get_param('mobikul.guest_checkout', 'False'))
        return temp

    def _default_order_mail_template(self):
        return self.env.ref('sale.email_template_edi_sale').id

    def fetch_products(self, **kwargs):
        """
        Extra Parameters: domain, limit, fields, offset, order
        """
        domain = _get_product_domain()
        result = {'offset': kwargs.get('offset', 0)}
        try:
            if 'domain' in kwargs:
                domain += literal_eval(kwargs['domain'])
        except:
            pass
        if 'barcode' in kwargs:
            domain += [('barcode', '=', kwargs['barcode'])]
        if 'search' in kwargs:
            for s in kwargs['search'].split(" "):
                domain += [('name', 'ilike', s)]
        if 'cid' in kwargs:
            domain += [('mobikul_categ_ids', 'child_of', int(kwargs['cid']))]

        mobikul = self.env['mobikul'].sudo().search([], limit=1)
        domain+= [('company_id','in',[mobikul.company_id.id,False])]
        ProductObj = self.env['product.template'].sudo()
        result['tcount'] = ProductObj.search_count(domain)
        limit  = mobikul.product_limit or kwargs.get('limit', 5)
        product_data = ProductObj.search(domain, limit=limit, offset=result["offset"], order=kwargs.get('order', 0))

        result['products'] = _getProductData(product_data, kwargs.get("context"))
        return result

    def _get_base_url(self):
        return self.env['ir.config_parameter'].get_param('web.base.url')


    def _default_language(self):
        lc = self.env['ir.default']._get('res.partner', 'lang')
        dl = self.env['res.lang'].search([('code', '=', lc)], limit=1)
        return dl.id if dl else self.env['res.lang'].search([]).ids[0]


    def _active_languages(self):
        return self.env['res.lang'].search([]).ids

    def _active_pricelist(self):
        return self.env['product.pricelist'].sudo().search([('selectable','=',True)]).ids

    def add_to_cart(self, product_id, set_qty, add_qty, context):
        Product = self.env["product.product"].sudo().browse(int(product_id))
        Partner = context.get("partner")
        if Product:
            if Partner:
                last_order = context.get('order').sudo()
                flag = 0
                resp = {}
                if last_order:
                    try:
                        resp = last_order.with_context(context)._cart_update(
                            product_id=int(product_id),
                            add_qty=add_qty and int(add_qty) or 0,
                            set_qty=set_qty and int(set_qty) or 0,
                            product_custom_attribute_values=False,
                            no_variant_attribute_values=False
                        )
                        flag = 1
                    except Exception as e:
                        return {'success': False, 'message': _('Exception Found : %r' % e.args[0])}
                else:
                    # Create Order
                    res = self._create_so(Partner, context)
                    last_order = res['order']
                    try:
                        resp = last_order.with_context(context)._cart_update(
                            product_id=int(product_id),
                            add_qty=add_qty and int(add_qty) or 0,
                            set_qty=set_qty and int(set_qty) or 0,
                            product_custom_attribute_values=False,
                            no_variant_attribute_values=False
                        )
                        flag = 1
                    except Exception as e:
                        return {'success': False, 'message': _('Exception Found : %r' % e.args[0])}
                if resp.get('warning'):
                    flag = 0
                    result =  {
                        'message': resp['warning'],
                        'success': False
                    }
                if flag:
                    result = {
                        'message': _('Added Successfully.'),
                        'cartCount': last_order.cart_count,
                        'productName': Product.display_name,
                        'success': True
                    }
                return result
            else:
                result = {'success': False, 'message': _('Account not found !!!')}
                return result
        else:
            result = {'success': False, 'message': _('Product not found !!!')}
            return result

    def sellerDashboardData(self, seller_Obj):
        prdObj = self.env['product.template'].sudo()
        SaleOrderLine = self.env['sale.order.line'].sudo()
        approved_count = prdObj.search_count(
            [('marketplace_seller_id', '=', seller_Obj.id), ('status', '=', 'approved')])
        pending_count = prdObj.search_count(
            [('marketplace_seller_id', '=', seller_Obj.id), ('status', '=', 'pending')])
        rejected_count = prdObj.search_count(
            [('marketplace_seller_id', '=', seller_Obj.id), ('status', '=', 'rejected')])
        new_sol_count = SaleOrderLine.search_count(
            [('marketplace_seller_id', '=', seller_Obj.id), ('marketplace_state', '=', 'new')])
        approved_sol_count = SaleOrderLine.search_count(
            [('marketplace_seller_id', '=', seller_Obj.id), ('marketplace_state', '=', 'approved')])
        shipped_sol_count = SaleOrderLine.search_count(
            [('marketplace_seller_id', '=', seller_Obj.id), ('marketplace_state', '=', 'shipped')])
        temp = {
            "approved_productCount": approved_count,
            "pending_productCount": pending_count,
            "rejected_productCount": rejected_count,
            "new_solCount": new_sol_count,
            "approved_solCount": approved_sol_count,
            "shipped_solCount": shipped_sol_count,
            "total": {
                "label": "Total Amount",
                "value": seller_Obj.total_mp_payment
            },
            "balance": {
                "label": "Balance Amount",
                "value": seller_Obj.balance_mp_payment
            },

        }
        return temp

    def _getPaymentTerms(self):
        mobikul = self.sudo().search([], limit=1)
        temp = {
            "paymentTerms": {
                "paymentShortTerms": mobikul.payment_short_terms,
                "paymentLongTerms": mobikul.payment_long_terms
            }
        }
        return temp

    def _getdefaultWebsite_id(self):
        website_id = self.env['website'].search([], limit=1)
        return website_id.id

    def _getdefaultCompany_id(self):
        comp_id = self.env['res.company'].search([], limit=1)
        return comp_id.id

    def generate_secret_key(self):
        uid = uuid.uuid4()
        self.api_key = str(uid)[14:]
        return True


    name = fields.Char('Mobikul App Title', default="Mobikul App", required=True)
    salesperson_id = fields.Many2one('res.users', string='Default Salesperson')
    salesteam_id = fields.Many2one('crm.team', string='Default Sales Team')
    api_key = fields.Char(string='API Secret key', default="dummySecretKey", required=True)
    firebase_auth_file = fields.Binary(string='Firebase Authentication File',attachment=True)
    color_scheme = fields.Selection([
        ('default', 'Default'),
        ('red-green', 'Red-Green'),
        ('light-green', 'Light Green'),
        ('deep-purple-pink', 'Deep Purple-Pink'),
        ('blue-orange', 'Blue Orange'),
        ('light-blue-red', 'Light Blue-Red')],
        string='Color Scheme', required=True,
        default='default',
        help="Color Options for your Mobikul App.")

    default_lang = fields.Many2one('res.lang', string='Default Language', default=_default_language,
                                   help="If the selected language is loaded in the mobikul, all documents related to "
                                   "this contact will be printed in this language. If not, it will be English.")

    language_ids = fields.Many2many('res.lang', 'mobikul_lang_rel',
                                    'mobikul_id', 'lang_id', 'Languages', default=_active_languages)
    pricelist_ids = fields.Many2many('product.pricelist', string='Pricelists',domain=[('selectable','=',True)],default=_active_pricelist)
    pricelist_id = fields.Many2one('product.pricelist', string='Default Pricelist')
    currency_id = fields.Many2one(
        'res.currency', related='pricelist_id.currency_id', string='Default Currency', readonly=True)
    order_mail_template = fields.Many2one('mail.template', string='Confirmation Email', readonly=True,
                                          default=_default_order_mail_template, help="Email sent to customer at the end of the checkout process")

    api_debug = fields.Boolean(default=False,string="Activate log",help="It is only use in case of any error occures in App")

    product_limit = fields.Integer(
        default=10, string='Limit Products per page', help='Used in Pagination', required=True)
    website_id = fields.Many2one('website', default=_getdefaultWebsite_id,
                                 help="select website id for the app")
    company_id = fields.Many2one('res.company', default=_getdefaultCompany_id,
                                 help="select company id for the app")
    country_ids = fields.Many2many('res.country', 'mobikul_coumtry_rel',
                                   'mobikul_id', 'country_id', string='Countries')
    enable_term_and_condition = fields.Boolean(default=False, string='Enable Terms and Condition')
    signup_terms_and_condition = fields.Html(string='Terms and Condition', translate=True)
    privacy_policy = fields.Char(string='Privacy Policy', help="Add your website privacy policy URL")
    payment_short_terms = fields.Html(string='Payment Short Terms', required=True,
                                      default="Payment short Terms and Conditions Decription", translate=True)
    payment_long_terms = fields.Html(string='Payment Long Terms', required=True,
                                     default="Payment long Terms and Conditions Decription", translate=True)
    walk_through_ids = fields.Many2many('mobikul.walkthrough',string='Walk Through')
    homepage_id = fields.Many2one('mobikul.homepage.configuration', string= "Homepage")

    def unlink(self):
        raise UserError(_('You cannot remove/deactivate this Configuration.'))

    def _getApiDetails(self,url,method,body,type=None,headers=None,response=None):
        now = datetime.now().strftime('%M%S')
        if(type == "request"):
            _logger.info(f"\n\n\n\n{'*'*57} Mobikul Request {'*'*23}{now}{'*'*39}\n\nUrl:{url}\nType:{method}\nBody data:{body}\nRequest:{headers}{'*'*142}")
        if(type == "response"):
            _logger.info(f"\n{'*'*57} Mobikul Response {'*'*23}{now}{'*'*39}\n\n{response}\n\n{'*'*142}\n\n\n\n")

    @api.onchange('firebase_auth_file')
    def _onchange_account_type(self):
        dir_path = os.path.realpath(os.path.join(os.path.dirname(__file__), "../static/src"))
        file_path = f'{dir_path}/firebase-auth.json'
        file_size = os.path.getsize(file_path)
        if file_size:
            f = open(file_path,"r+")
            f.seek(0)
            f.truncate()


class MobikulBanners(models.Model):
    _name = 'mobikul.banners'
    _description = 'Mobikul Banner Class'
    _order = "sequence, name"

    name = fields.Char('Title', required=True, translate=True)
    active = fields.Boolean(default=True)
    description = fields.Text('Description', translate=True)
    image = fields.Binary('Image', attachment=True)
    banner_action = fields.Selection([
        ('product', 'Open Product Page'),
        ('category', 'Open Category Page'),
        ('custom', 'Open Custom Collection Page'),
        ('none', 'Do nothing')],
        string='Action to be triggered', required=True,
        default='none',
        help="Define what action will be triggerred when click/touch on the banner.")
    product_id = fields.Many2one('product.template', string='Choose Product')
    category_id = fields.Many2one('mobikul.category', string='Choose Category')
    product_ids = fields.Many2many('product.template', string='Choose Products')
    homepage_id = fields.Many2one('mobikul.homepage', string='Homepage')
    url = fields.Char(
        'Image URL', help="Static URL of Banner Image, used when banner`s image is not present.")
    date_published = fields.Datetime('Publish Date')
    date_expired = fields.Datetime('Expiration Date')
    sequence = fields.Integer(default=10, help='Display order')
    total_views = fields.Integer('Total # Views', default=0, readonly=True)

    @api.model_create_multi
    def create(self, values):
        for value in values:
            if not value.get('image') and not value.get('url'):
                raise UserError(_('Please upload Banner`s Image or enter Image URL'))
            if not value.get('date_published'):
                value['date_published'] = datetime.now()
        return super(MobikulBanners, self).create(values)

    # crone for auto inactive expire banners
    @api.model
    def process_inactive_mobikul_banner(self):
        banner = self.sudo().search([])
        inactive_MobBanners = []
        for b in banner:
            if b.date_expired:
                if fields.Date.from_string(fields.Datetime.now()) > fields.Date.from_string(b.date_expired):
                    inactive_MobBanners.append(b)
        for i in inactive_MobBanners:
            i.active = False

# method to check expire banners
    @api.model
    def remove_expireBanners(self):
        banner = self.sudo().search([])
        MobBanners = []
        for b in banner:
            if b.date_expired:
                if fields.Date.from_string(fields.Datetime.now()) <= fields.Date.from_string(b.date_expired):
                    MobBanners.append(b)
            else:
                MobBanners.append(b)
        return MobBanners


class MobikulCategory(models.Model):
    _name = 'mobikul.category'
    _description = 'Mobikul Category'
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    parent_id = fields.Many2one('mobikul.category', string='Parent Category', index=True)
    child_id = fields.One2many('mobikul.category', 'parent_id', string='Children Categories')
    banner = fields.Binary('Banner', attachment=True)
    icon = fields.Binary('Icon', attachment=True)
    sequence = fields.Integer(default=10, help='Display order')
    complete_name = fields.Char(
        'Complete Name', compute='_compute_complete_name',
        store=True,recursive=True)
    # this field is added for mobikul category merge
    website_cat_id = fields.Many2one('product.public.category', 'Website Category')

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = '%s / %s' % (
                    category.parent_id.complete_name, category.name)
            else:
                category.complete_name = category.name

    @api.constrains('parent_id')
    def check_parent_id(self):
        if not self._check_recursion():
            raise ValueError(_('Error ! You cannot create recursive categories.'))

    def name_get(self):
        res = []
        for category in self:
            names = [category.name]
            parent_category = category.parent_id
            while parent_category:
                names.append(parent_category.name)
                parent_category = parent_category.parent_id
            res.append((category.id, ' / '.join(reversed(names))))
        return res

    # method call from server action
    @api.model
    def sync_category(self):
        action = self.env.ref('mobikul.mobikul_sync_cat_action').read()[0]
        action['views'] = [(self.env.ref('mobikul.mobikul_sync_cat_form').id, 'form')]
        action['context'] = self._context
        return action

    # def _compute_products(self):
    #   read_group_res = self.env['product.template'].read_group([('categ_id', 'in', self.ids)], ['categ_id'], ['categ_id'])
    #   group_data = dict((data['categ_id'][0], data['categ_id_count']) for data in read_group_res)
    #   for categ in self:
    #       categ.product_count = group_data.get(categ.id, 0)


class MobikulSyncCategory(models.Model):
    _name = "mobikul.sync.category"
    _description = " Mobikul category mappings"

    sync_type = fields.Selection([
        ('name', 'Only Name'),
        ('name_seq', 'Name and Sequence'),
        ('name_parent', 'Name and Parent Category'),
        ('name_parent_seq', 'Name, Parent Category and Sequence'), ], 'Sync Type', default='name_parent_seq',
        help="Sync mobikul category on the basis of Selection")

    def show_msg_wizard(self, msg):
        partial_id = self.env['wk.wizard.message'].create({'text': msg})
        return {
            'name': "Message",
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'wk.wizard.message',
            'res_id': partial_id.id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
        }

    def sync_mobikul_cat_with_web_cat(self):
        isCatMerge = self.env['ir.module.module'].sudo().search(
            [('state', '=', 'installed'), ('name', '=', 'mobikul_cat_merge')]) and True or False
        if isCatMerge:
            mobikul_catg_ids = self.env['mobikul.category'].search(
                [("id", "in", self._context.get('active_ids'))])
            if not self.sync_type:
                raise UserError(_("Please select the Sync Type."))
            for mob_cat in mobikul_catg_ids:
                if mob_cat.website_cat_id.id:
                    if self.sync_type == "name":
                        mob_cat.name = mob_cat.website_cat_id.name
                    elif self.sync_type == "name_parent":
                        mob_cat.name = mob_cat.website_cat_id.name
                        mob_cat.parent_id = mob_cat.website_cat_id.parent_id.mobikul_cat_id.id
                    elif self.sync_type == "name_parent_seq":
                        mob_cat.name = mob_cat.website_cat_id.name
                        mob_cat.parent_id = mob_cat.website_cat_id.parent_id.mobikul_cat_id.id
                        mob_cat.sequence = mob_cat.website_cat_id.sequence
                    elif self.sync_type == "name_seq":
                        mob_cat.name = mob_cat.website_cat_id.name
                        mob_cat.sequence = mob_cat.website_cat_id.sequence

                else:
                    _logger.info("MESAGE :Website category is not present in Mobikul Caegory")
            if self.sync_type == "name":
                message = "Done! name are synced with mobikul category from Website category."
            elif self.sync_type == "name_seq":
                message = "Done! name and sequence are synced with mobikul category from Website category."
            elif self.sync_type == "name_parent":
                message = "Done! name and parent category are synced with mobikul categories from Website category."
            elif self.sync_type == "name_parent_seq":
                message = "Done! name, sequence and parent category are synced with mobikul categories from Website category."
        else:
            message = "Install the Mobikul Category Merge Module First"
        return self.show_msg_wizard(message)


class MobikulPushNotificationTemplate(models.Model):
    _name = 'mobikul.push.notification.template'
    _description = 'Mobikul Push Notification Templates'
    _order = "name"

    def _addMe(self, data):
        self.env["mobikul.notification.messages"].sudo().create(data)
        return True

    def _get_firebase_auth_file(self):
        mobikul = self.env['mobikul'].sudo().search([], limit=1)
        dir_path = os.path.realpath(os.path.join(os.path.dirname(__file__), "../static/src"))
        file_path = f'{dir_path}/firebase-auth.json'
        file_size = os.path.getsize(file_path)
        try:
            if file_size == 0:
                # os.chmod(file_path,mode = 0o777)
                firebase_auth_file_bin = mobikul.firebase_auth_file
                firebase_auth_file_content = base64.b64decode(firebase_auth_file_bin)
                with open(file_path,"w+") as file:
                    file.write(firebase_auth_file_content.decode("utf-8"))
            return mobikul and file_path or ""
        except:
            pass

    @api.model
    def _pushMe(self, firebase_project_auth_file, payload_data, data=False):
        status = True
        summary = ""
        try:
            push_service = FCMAPI(auth_file=firebase_project_auth_file)
            summary = push_service.send([payload_data])
            if data:
                self._addMe(data)
        except Exception as e:
            status = False
            summary = "Error: %r" % e
        return [status, summary]

    @api.model
    def _send(self, to_data, customer_id=False, max_limit=20):
        """
        to_data = dict(token or topic)
        """
        if type(to_data) != dict:
            return False
        if not to_data.get("token", False) and not to_data.get("topic", False):
            if not customer_id:
                return False
            reg_data = self.env['fcm.registered.devices'].sudo().search_read(
                [('customer_id', '=', customer_id)], limit=max_limit, fields=['token'])
            if not reg_data:
                return False
            to_data = {
                "token": [r['token'] for r in reg_data]
            }
        notification = dict(title=self.notification_title,
                            body=self.notification_body)
        message = dict(notification=notification)

        data_message = dict(type="", id="", domain="", image="", name="")
        if self.banner_action == 'product':
            data_message['type'] = 'product'
            data_message['id'] = str(self.product_id.id)
            data_message['name'] = self.product_id.name
        elif self.banner_action == 'category':
            data_message['type'] = 'category'
            data_message['id'] = str(self.category_id.id)
            data_message['name'] = self.category_id.name
        elif self.banner_action == 'custom':
            data_message['type'] = 'custom'
            data_message['domain'] = "[('id','in',%s)]" % self.product_ids.ids
            data_message['name'] = self.notification_title
        elif self.banner_action_lastorder == 'lastOrder' and self.condition == 'orderplaced':
            data_message['type'] = 'lastOrder'
            data_message['id'] = self._context.get("order") and str(self._context.get("order").id) or ""
            data_message['name'] = self._context.get("order") and self._context.get("order").name or ""
        else:
            data_message['type'] = 'none'
        image = _get_image_url(self._context.get('base_url'),self._context.get('active_model') or 'mobikul.push.notification.template', self.id, 'image', self.write_date)
        if not self.image:
            image = ""
        
        data_message['image'] = image
        data_message['notificationId'] = str(random.randint(1, 99999))

        message['data'] = data_message

        message['android'] = {"notification":{
            "image": image,
            "sound": "default"
        }}
        message['apns'] = {"payload": {
            "aps": {
                'mutable-content': 1,
                "sound": "default"
                }},
            "fcm_options": {
                "image": image,
        }}

        if self.notification_color:
            message['android']['notification']['color'] = self.notification_color
            message['apns']['payload']['aps']['color'] = self.notification_color
        if self.notification_tag:
            message['android']['notification']['tag'] = self.notification_tag
            message['apns']['payload']['aps']['tag'] = self.notification_tag

        domain = [('res_model', '=', self._name),
            ('res_field', '=', 'image'),
            ('res_id', 'in', [self.id])]
        attachment = self.env['ir.attachment'].sudo().search(domain)

        if customer_id:
            data = dict(
                title=self.notification_title, body=self.notification_body, customer_id=customer_id,
                banner=attachment.datas, datatype='default'
            )
        if to_data.get("topic"):
            message.update(to_data)
            fcm_payload = {"message":message}
            result = self._pushMe(self._get_firebase_auth_file(), json.dumps(fcm_payload).encode('utf8'), customer_id and data or False)
        lst_error = []
        if to_data.get("token"):
            for reg_id in to_data.get("token"):
                message.update({"token":reg_id})
                fcm_payload = {"message":message}
                result = self._pushMe(self._get_firebase_auth_file(), json.dumps(fcm_payload).encode('utf8'), customer_id and data or False)
                if len(to_data.get("token"))>1 and result[0] == False:
                    lst_error.append(reg_id)
        if len(lst_error):
            result.append(lst_error)
        return result

    name = fields.Char('Name', required=True, translate=True)
    notification_color = fields.Char('Color', default='PURPLE')
    notification_tag = fields.Char('Tag')
    notification_title = fields.Char('Title', required=True, translate=True)
    active = fields.Boolean(default=True, copy=False)
    notification_body = fields.Text('Body', translate=True)
    image = fields.Binary('Image', attachment=True)
    banner_action = fields.Selection([('product', 'Open Product Page'),('category', 'Open Category Page'),('custom', 'Open Custom Collection Page'),('none','Do nothing')],
        string='Action', required=True,
        default='none',
        help="Define what action will be triggerred when click/touch on the banner.")
    banner_action_lastorder = fields.Selection([('lastOrder','Last Placed Order'),('none','Do nothing')],
        string='Action', required=True,
        default='lastOrder',
        help="Define what action will be triggerred when click/touch on the banner.")
    product_id = fields.Many2one('product.template', string='Choose Product')
    product_ids = fields.Many2many('product.template', string='Choose Products')
    category_id = fields.Many2one('mobikul.category', string='Choose Category')
    device_id = fields.Many2one('fcm.registered.devices', string='Select Device')
    total_views = fields.Integer('Total # Views', default=0, readonly=True, copy=False)
    condition = fields.Selection([
        ('signup', 'Customer`s SignUp'),
        ('login', "Customer`s Login"),
        ('orderplaced', "Order Placed")
    ], string='Condition', required=True, default='signup')

    def dry_run(self):
        self.ensure_one()
        to_data = dict(token=[self.device_id and self.device_id.token or ""])
        result = self._send(
            to_data, self.device_id and self.device_id.customer_id and self.device_id.customer_id.id or False)

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {}, name=_('%s(copy)') % self.name)
        return super(MobikulPushNotificationTemplate, self).copy(default)


class MobikulPushNotification(models.Model):
    _name = 'mobikul.push.notification'
    _description = 'Mobikul Push Notification'
    _order = "activation_date, name"
    _inherit = ['mobikul.push.notification.template']

    @api.model
    def parse_n_push(self, max_limit=20, registration_ids=None):
        to_data = dict()
        mobikul = self.env["mobikul"].sudo().search([],limit=1)
        app_lang = mobikul.default_lang and mobikul.default_lang.code or "en_US"
        if self.notification_type == 'token-auto':
            reg_data = self.env['fcm.registered.devices'].sudo(
            ).search_read(limit=max_limit, fields=['token'])
            registration_ids = [r['token'] for r in reg_data]
        elif self.notification_type == 'token-manual':
            registration_ids = [d.token for d in self.device_ids]
        elif self.notification_type == 'group-based':
            if self.group_id:
                records = []
                for user in self.group_id.user_ids:
                    for tokenObj in user.partner_id.token_ids:
                        records.append(tokenObj)
                registration_ids = [d.token for d in records] or []
                if not registration_ids:
                    return [False, "Error: Exception('There was an error authenticating the sender account')"]
        elif self.notification_type == 'topic':
            to_data['topic'] = self.topic_id.name
        else:
            return [False, "Insufficient Data"]

        if registration_ids:
            to_data['token'] = registration_ids
        return self.with_context(lang=app_lang,lang_obj=self.env['res.lang']._lang_get(app_lang),base_url=request.httprequest.host_url)._send(to_data)

    summary = fields.Text('Summary', readonly=True)
    activation_date = fields.Datetime('Activation Date', copy=False)
    notification_type = fields.Selection([
        ('token-auto', 'Token-Based(All Reg. Devices)'),
        ('token-manual', 'Token-Based(Selected Devices)'),
        ('topic', 'Topic-Based'),
        ('group-based','Group-Based')
    ],
        string='Type', required=True,
        default='token-auto')
    topic_id = fields.Many2one('fcm.registered.topics', string='Choose Topic')
    group_id = fields.Many2one('fcm.groups', string='Group')
    device_ids = fields.Many2many('fcm.registered.devices', string='Choose Devices/Customers')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('hold', 'Hold'),
        ('error', 'Error'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')

    def action_cancel(self):
        for record in self:
            record.state = 'cancel'
        return True

    def action_confirm(self):
        for record in self:
            record.state = 'confirm'
        return True

    def action_draft(self):
        for record in self:
            record.state = 'draft'
        return True

    def action_hold(self):
        for record in self:
            record.state = 'hold'
        return True

    def push_now(self):
        for record in self:
            response = record.parse_n_push()
            record.state = response[0] and 'done' or 'error'
            if len(response) > 2:
                record.summary = str(response[1])+" The registration token is not a valid FCM registration token: "+str(response[2])
            else:
                record.summary = response[1]
        return True

    def duplicate_me(self):
        self.ensure_one()
        action = self.env.ref('mobikul.mobikul_push_notification_action').read()[0]
        action['views'] = [(self.env.ref('mobikul.mobikul_push_notification_view_form').id, 'form')]
        action['res_id'] = self.copy().id
        return action

    def _valid_field_parameter(self, field, name):
        return name == 'track_visibility' or super()._valid_field_parameter(field, name)



class MobikulProductSlider(models.Model):
    _name = 'mobikul.product.slider'
    _description = 'Mobikul Product Slider'
    _order = "sequence"

    def _products_count(self):
        r = {}
        for slider in self:
            slider.product_count = r.get(slider.id, len(slider.get_product_data({'count': True})))
        return r

    def action_view_products(self):
        products = self.get_product_data({'count': True})
        action = self.env.ref('mobikul.mobikul_product_template_action').read()[0]
        action['domain'] = [('id', 'in', products)]
        return action

    def get_product_data(self, context=None):
        context = context or {}
        orderBy = None#context.get('order', None)
        mlimit = context.get('limit', self.item_limit)
        moffset = context.get('offset', 0)
        prod_obj = self.env['product.template'].sudo()
        product_filter = _get_product_domain()
        mobikul = self.env['mobikul'].sudo().search([], limit=1)
        product_filter.append(('company_id','in',[mobikul.company_id.id,False]))
        if self.product_selection == "manual":
            product_filter.append(('id', 'in', self.product_ids._ids))
        elif self.product_based_on == 'new':
            orderBy = 'id desc'
        elif self.product_based_on == 'iCategory':
            product_filter.append(
                ('categ_id', '=', self.icategory_id and self.icategory_id.id or False))
        elif self.product_based_on == 'wCategory':
            product_filter.append(
                ('public_categ_ids', '=', self.wcategory_id and self.wcategory_id.id or False))
        elif self.product_based_on == 'mCategory':
            product_filter.append(
                ('mobikul_categ_ids', '=', self.mcategory_id and self.mcategory_id.id or False))
        all_prods = prod_obj.search(product_filter, order=orderBy)
        if 'count' in context:
            return all_prods._ids
        else:
            product_data = prod_obj.search(
                product_filter, limit=mlimit, offset=moffset, order=orderBy)
        result = {'tcount': len(all_prods), 'offset': moffset}
        result['products'] = _getProductData(product_data, context)
        return result

    name = fields.Char('Slider Title', required=True, translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10, help='Display order', required=True)
    description = fields.Text('Description', translate=True)
    display_banner = fields.Boolean('Display Banner', default=False)
    banner = fields.Binary('Banner', attachment=True)
    homepage_id = fields.Many2one('mobikul.homepage', string='Homepage')
    url = fields.Char('Link URL', help="Used when someone click on banner/view-all button.")
    product_ids = fields.Many2many('product.template', string='Choose Products')
    total_views = fields.Integer('Total # Views', default=0, readonly=True)
    item_limit = fields.Integer('Maximum no. of products in a slider', default=5, required=True)
    item_display_limit = fields.Integer(
        'Display no. of Products in a slider(per row)', default=5, required=True)
    slider_mode = fields.Selection([
        ('default', 'Default(Slide)'),
        ('fixed', 'Fixed'),
    ],
        string='Slider Mode', required=True,
        default='default',
        help="Define which type of behaviour you want with your Slider.")
    product_selection = fields.Selection([
        ('manual', 'Manual'),
        ('automatic', 'Automatic'),
    ],
        string='Selection Criteria', required=True, default='automatic')
    product_based_on = fields.Selection([
        ('new', 'Newly created'),
        ('iCategory', 'Internal Category'),
        ('mCategory', 'Mobikul Category'),
        ('wCategory', 'Website Category'),
    ],
        string='Based on', default='new')
    mcategory_id = fields.Many2one('mobikul.category', string='Mobikul Category')
    wcategory_id = fields.Many2one('product.public.category', string='Website Category')
    icategory_id = fields.Many2one('product.category', string='Internal Category')
    product_count = fields.Integer(compute='_products_count', string='# Products')
    bk_color = fields.Char('Background Color')

    @api.model_create_multi
    def create(self, vals):
        alreadyExist = self.env['mobikul.product.slider'].search([('homepage_id','=',vals[0]['homepage_id'])])
        if alreadyExist or len(vals)>1:
            raise UserError('You can not create a more than one slider for existing record.')
        else:
            return super(MobikulProductSlider, self).create(vals)


class FcmRegisteredDevices(models.Model):
    _name = 'fcm.registered.devices'
    _description = 'All Registered Devices on FCM for Push Notifications.'
    _order = 'write_date desc'

    @api.depends('name')
    def _compute_display_name(self):
        res = []
        for record in self:
            name = record.customer_id and record.customer_id.display_name or ''
            record.display_name = "%s(DeviceId:%s)"%(name,record.device_id)
            res.append((record.id, "%s(DeviceId:%s)"%(name,record.device_id)))
        return res

    name = fields.Char('Name')
    token = fields.Text('FCM Registration ID', readonly=True)
    device_id = fields.Char('Device Id', readonly=True)
    customer_id = fields.Many2one('res.partner', string="Customer", readonly=True, index=True)
    active = fields.Boolean(default=True, readonly=True)
    # write_date = fields.Datetime(string='Last Update', readonly=True, help="Date on which this entry is created.")
    description = fields.Text('Description', readonly=True)
    last_guest_so_id = fields.Many2one('sale.order', string='Last Order from Guest')


class FcmRegisteredTopics(models.Model):
    _name = 'fcm.registered.topics'
    _description = 'All Registered Topics for Push Notifications.'

    name = fields.Char('Topic Name', required=True)


class FcmGroups(models.Model):
    _name = 'fcm.groups'
    _description = 'To Send notification to a group of customers'

    name = fields.Char('Group Name', required=True)
    user_ids = fields.Many2many('res.users',string = 'Users')



class MobikulNotificationMessages(models.Model):
    _name = 'mobikul.notification.messages'
    _description = 'Mobikul Notification Messages'

    name = fields.Char('Message Name', default='/', index=True, copy=False, readonly=True)
    title = fields.Char('Title')
    subtitle = fields.Char('Subtitle')
    body = fields.Text('Body')
    icon = fields.Binary('Icon')
    banner = fields.Binary('Banner')
    is_read = fields.Boolean('Is Read', default=False, readonly=True)
    customer_id = fields.Many2one('res.partner', string="Customer", index=True)
    active = fields.Boolean(default=True, readonly=True)
    period = fields.Char('Period', compute='_compute_period')
    datatype = fields.Selection([
        ('default', 'Default'),
        ('order', 'Order')],
        string='Data Type', required=True,
        default='default',
        help="Notification Messages Data Type for your Mobikul App.")

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('mobikul.notification.messages')
        return super(MobikulNotificationMessages, self).create(vals)

    def _compute_period(self):
        for i in self:
            i.period = _easy_date(i.create_date)
