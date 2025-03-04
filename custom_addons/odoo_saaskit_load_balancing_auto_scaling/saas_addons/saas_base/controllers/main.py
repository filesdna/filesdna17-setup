# -*- coding: utf-8 -*-
from odoo.http import request
# from pragmatic_saas.saas_base.admin_user import ADMINUSER_ID
from odoo import http
from odoo import api, fields, models
import json
import re
import datetime
#from odoo import pooler
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo import tools
from odoo.addons.web.controllers.webclient import WebClient
from odoo.tools import config
import logging
_logger = logging.getLogger(__name__)
ADMINUSER_ID = 2


# class InheritedWebsiteSale(WebsiteSale):
    
    # @http.route('/shop/payment', type='http', auth="public", website=True, sitemap=False)
    # def shop_payment(self, **post):
    #     print("3"*888)
    #     render_values = {}
    #     return request.render("website_sale.payment", render_values)

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

    #     return super(InheritedWebsiteSale, self).shop_payment(**post)
class website_saas(http.Controller):  
    
    
    @http.route(['/saas/getvalues'], type='http', auth="public", website=True, csrf=False)
    def getvalues(self,  **post):
        values = {}
        cr = request.cr 
        if post:
            cr.execute('select no_of_users from tenant_database_list where id=%s'%post['id'])
            users = cr.fetchone()
            if users:
                values = {'no_of_users':users[0] }
                
            #=======================================================================
            # check for product is already purchased or not
            #=======================================================================
            order = request.website.sale_get_order()
            checkout_product_dict = {}
            for line in order.order_line:
                checkout_product_dict[line.product_id.id] = line.product_id.name_template
            
            cr.execute('select name from tenant_database_list where id=%s'%post['id'])
            name = cr.fetchone()
            if name:
                name = name[0]
            order_obj = request.env['sale.order'].sudo()
            sale_ids = order_obj.search([('instance_name', '=', name), ('id', '!=', order.id)])
            if sale_ids:
                for line in sale_ids:
                    if line.product_id.id in checkout_product_dict:
                        values['exist'] = checkout_product_dict[line.product_id.id]
                        break
        return json.dumps(values)
    
    
    
    @http.route(['/saas/get_current_users'], type='http', auth="public", website=True, csrf=False)
    def get_current_users(self,  **post):
        values = ''
        cr = request.cr
        
        cr.execute('select no_of_users from tenant_database_list where id=%s'%post['id'])
        
        users = cr.fetchone()
        if users:
            values = {'no_of_users':users[0] }
            
        return json.dumps(values)
        
    
    
    @http.route(['/saas/check_db_already_exist'], type='http', auth="public", website=True, csrf=False)
    def check_db_already_exist(self,  **post):
        #=======================================================================
        # To check entered DB name is already exist or not
        #=======================================================================
        values = ''
        request.cr.execute("SELECT datname FROM pg_database;")
        for item in request.cr.fetchall():
            if post['name'] == item[0]:
                values = 1
                break
        return json.dumps(values)
    
    
    
    
    @http.route(['/saas/get_product_qty'], type='http', auth="public", website=True, csrf=False)
    def get_product_qty(self,  **post):
        #=======================================================================
        # To check entered DB name is already exist or not
        #=======================================================================
        values = ''
        order = request.website.sale_get_order()
        for line in order.order_line:
            values = line.product_uom_qty
            break
        return json.dumps(values)

    ## Override the Controller for web translation#####
    @http.route('/website/translations/<string:unique>', type='http', auth="public", website=True)
    def get_website_translations(self, unique, lang=None, mods=None):
        _logger.info("Language===>>>>>>>>>>>>>%s",lang)
        IrHttp = request.env['ir.http'].sudo()
        modules = IrHttp.get_translation_frontend_modules()
        _logger.info("MODULES===>>>>>>>>>>>>>%s",modules)
        _logger.info("\n\n\n\nCOntext===>>>>>>>>>>%s",request.context)
        website_id = request.env['website'].sudo().search([('id','=',int(request.context.get('website_id')))])
        _logger.info("WEBSITE DEFAULR LANG==>>>>>%s",website_id.default_lang_id)
        if mods:
            modules += mods
        return WebClient().translations(unique, mods=','.join(modules), lang=lang)
    
    
    
class website_title(models.Model):
    _inherit = 'website'
       
    get_brand_name=fields.Char('Brand Name', size=64)
       
    def get_brand_name(self, **args):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        brand_name = ICPSudo.search([('key', '=', 'brand_name')]).value
        return brand_name
