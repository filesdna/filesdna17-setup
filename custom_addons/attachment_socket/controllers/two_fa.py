# -*- coding: utf-8 -*-
from odoo import http
import requests
import re
import odoo
from odoo.exceptions import AccessError, UserError, AccessDenied
from odoo.http import request
import json
import base64
from werkzeug.utils import redirect
from odoo import http
import werkzeug.exceptions
from odoo.http import request
from odoo.http import Response
from werkzeug.exceptions import (HTTPException, BadRequest, Forbidden,
                                 NotFound, InternalServerError)
from odoo.tools import config

class FAAuthentaction(http.Controller):
    @http.route('/api/login/totp',type='json', auth='public', methods=['POST'])
    def web_totp(self, redirect=None, **kwargs):
        user = request.env['res.users'].browse(request.session.pre_uid)  
        totp_token = kwargs.get('totp_token')      
        if user and totp_token:
            try:
                with user._assert_can_auth(user=user.id):
                    user._totp_check(int(re.sub(r'\s', '', totp_token)))
            except AccessDenied as e:
                message = {"result":{'success': False,'message': 'Verification failed, please double-check the 6-digit code'}}
                return werkzeug.exceptions.abort(Response(json.dumps(message), status=403))
            except ValueError:
                message = {"result":{'success': False,'message': 'Invalid authentication code format.'}}
                return werkzeug.exceptions.abort(Response(json.dumps(message), status=400))
            else:
                cookies = request.httprequest.cookies
                request.session.finalize(request.env)
                request.update_env(user=request.session.uid)
                request.update_context(**request.session.context)
                response = {}
                user_id = request.env['res.users'].sudo().search([('id', '=', user.id)], limit=1)
                user_auth_token = request.env['auth.token'].sudo().search([('user_id', '=', user.id)]).name
                response.update({'auth_token_dna':user_auth_token})
                response.update({'success':True})
                request.session.touch()
                return response

        