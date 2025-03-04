# -*- coding: utf-8 -*-
from odoo import http
import requests
import math
import odoo
from odoo.exceptions import AccessError, UserError, AccessDenied
from odoo.http import request
import json
import base64
from werkzeug.utils import redirect
from odoo import http
import werkzeug.exceptions
from odoo.http import Response
from werkzeug.exceptions import (HTTPException, BadRequest, Forbidden,
                                 NotFound, InternalServerError)



class DMSEditFlag(http.Controller):
    @http.route('/api/dms/edit-flag', auth='user', type='json', methods=['POST'], csrf=False)
    def edit_flag(self, **kw):
        email = kw.get('email')
        file_id = kw.get('file_id')
        current_date = kw.get('current_date')
        user = request.env['res.users'].search([('login','=',email)]).id
        file = request.env['dms.file'].search([('id','=',file_id)])
        file.write({
            "write_uid":user,
            "write_date": current_date
        })

    @http.route('/react/home', type='http', auth='public', website=True)
    def react_home(self, **kwargs):
        data_path_value = kwargs.get('data_path')
        return http.request.render('dms_editor.view_editor_template_home', {
            'data_path': data_path_value,
        })

    @http.route('/qrdetails/<string:data_path>', type='http', auth='public', website=True)
    def qrdetails(self, data_path, **kwargs):
        return http.request.render('dms_editor.view_qrdetails_template_home', {
            'data_path': data_path,
        })


