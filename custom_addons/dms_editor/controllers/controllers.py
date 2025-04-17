# -*- coding: utf-8 -*-
from odoo import http
import requests
import math
import odoo
from odoo.exceptions import AccessError, UserError, AccessDenied
from odoo.http import request
import json
import base64
import random
from werkzeug.utils import redirect
from odoo import http
import werkzeug.exceptions
from odoo.http import Response
from werkzeug.exceptions import (HTTPException, BadRequest, Forbidden,
                                 NotFound, InternalServerError)
from odoo.addons.dms_editor.services.blockchain import BlockchainService



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

    @http.route('/api/user_info', type='http', auth='public',methods=['GET'])
    def user_info(self):
        bc = BlockchainService()
        current_user = request.env.user
        if not current_user.blockchain_uid:
            random_string = ''.join(random.choices("0123456789abcdefghiklmnopqrstuvwxyz", k=24))
            prefix = "filesdna|"
            current_user.write({'blockchain_uid':f"{prefix}{random_string}"})
        if not current_user.bc_account:
            bc_acc = bc.create_account_in_blockchain(current_user.blockchain_uid)
            current_user.write({'bc_account': bc_acc })
        
        user_verification = request.env['user.verification'].sudo().search([('user_id','=',current_user.id)])
        if not user_verification:
            user_verification = request.env['user.verification'].sudo().create({'user_id':current_user.id})
        response = Response(
            json.dumps({
                'data':{
                'user_id': current_user.id,
                'sub': current_user.id,
                'first_name': current_user.name,
                'last_name': '',
                'email': current_user.email,
                'company_name': current_user.company_id.name,
                'user_verification':{
                    'is_verify_liveness':user_verification.is_verify_liveness,
                    'is_verify_voice':user_verification.is_verify_voice,
                },
                'is_verify_liveness':user_verification.is_verify_liveness,
                'is_verify_voice':user_verification.is_verify_voice,
                },
                'success': True
            }),
            content_type='application/json',
            status=200
        )
        return response

