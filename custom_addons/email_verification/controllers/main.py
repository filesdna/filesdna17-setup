
#  -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2018-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE URL <https://store.webkul.com/license.html/> for full copyright and licensing details.
#################################################################################
import logging
from odoo import http
from odoo.http import request
from odoo.tools.translate import _
import werkzeug.utils
from odoo.addons.web.controllers.home import Home
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.auth_signup.controllers.main import AuthSignupHome

_logger = logging.getLogger(__name__)


class Home(Home):

    @http.route('/web/email/verification', type='http', auth="none")
    def web_email_verification(self, redirect=None, **kw):
        res = request.env['res.users'].wk_verify_email(kw)        
        return request.render('email_verification.email_verification_template',{'status':res['status'],'msg':res['msg']})

    @http.route('/resend/email', type='http', auth='public', website=True)
    def resend_email(self, *args, **kw):
        user = request.env['res.users']
        user_id = user.browse([request.uid])
        post_params = ''
        if not user_id.wk_token_verified:
            user.sudo().with_context(website=request.website.id).send_verification_email(request.uid)

        else:
            href = request.httprequest.referrer
            
            if '#' in href:
                href = href + '&is_verified=True'
            else:
                href = href + '#is_verified=True'
            return request.redirect(href)
        return request.redirect('/my')


class WebsiteSale(WebsiteSale):
    
    @http.route()
    def shop_payment(self, **post):
        res = super(WebsiteSale,self).shop_payment(**post)
        
        if(request.website.check_email_is_validated()=='verified'):
            return res
        else:
            return request.redirect(request.httprequest.referrer or '/shop/cart')    
        return res


class AuthSignupHome(AuthSignupHome):

    def do_signup(self, qcontext):
        """ Shared helper that creates a res.partner out of a token """
        values = self._prepare_signup_values(qcontext)
        values['signup_from_website'] = True
        if hasattr(request, 'website'):
            values['website'] = request.website.id
        self._signup_with_values(qcontext.get('token'), values)
        request.env.cr.commit()
