# -*- coding: utf-8 -*-
from odoo import http
import requests
import odoo
from odoo.exceptions import AccessError, UserError, AccessDenied
from odoo.http import request
import json
from werkzeug.utils import redirect
from odoo import http
import werkzeug.exceptions
from odoo.http import Response
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from werkzeug.exceptions import (HTTPException, BadRequest, Forbidden,
                                 NotFound, InternalServerError)
from odoo.tools import config

class CustomRedirect(http.Controller):
    @http.route('/web/session/authenticate', type='json', auth="none")
    def authenticate(self, db, login, password, base_location=None):
        try:
            if not http.db_filter([db]):
                raise AccessError("Database not found.")
            pre_uid = request.session.authenticate(db, login, password)
            if pre_uid != request.session.uid:
                # Crapy workaround for unupdatable Odoo Mobile App iOS (Thanks Apple :@) and Android
                # Correct behavior should be to raise AccessError("Renewing an expired session for user that has multi-factor-authentication is not supported. Please use /web/login instead.")
                return {"2FA":True,'uid': None}

            request.session.db = db
            registry = odoo.modules.registry.Registry(db)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, request.session.uid, request.session.context)
                if not request.db and not request.session.is_explicit:
                    # request._save_session would not update the session_token
                    # as it lacks an environment, rotating the session myself
                    http.root.session_store.rotate(request.session, env)
                    request.future_response.set_cookie(
                        'session_id', request.session.sid,
                        max_age=http.SESSION_LIFETIME, httponly=True
                    )
                    
                response = env['ir.http'].session_info()
                user_id = request.env['res.users'].sudo().search([('login', '=', login)], limit=1).id
                user_auth_token = request.env['auth.token'].sudo().search([('user_id', '=', user_id)]).name
                response.update({'auth_token_dna':user_auth_token})
                response.update({'2FA':False})
                return response
    
        except:
            message = {'message':'user email or password is incorrect'}
            message = json.dumps(message)
            return werkzeug.exceptions.abort(Response(message,status=403)) 
