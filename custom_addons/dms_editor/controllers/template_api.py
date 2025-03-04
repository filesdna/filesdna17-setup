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
from odoo import http,fields
from odoo.http import request
from odoo.addons.web.controllers.home import Home
from odoo.addons.web.controllers.session import Session
from odoo.addons.web.controllers.webclient import WebClient
from datetime import datetime, timedelta
from odoo.http import Response
from datetime import date, datetime
import requests
import json
import logging

_logger = logging.getLogger(__name__)


class TemplateAPI(http.Controller): 
    @http.route('/api/attachments/file-directories', auth='none', type='json', methods=['POST'], csrf=False)
    def dir_list_temp(self,**kw):    
        email = kw.get('login')
        domain = [('login','=',email)]
        uid = request.env['res.users'].sudo().search(domain).id
        result = []
        # Retrieve page number and page limit from the parameters or set defaults
        access_group = request.env['dms.access.group'].sudo().search([])
        for group in access_group:
            _logger.info(f"dir1:{group.users.ids}")
            _logger.info(f"uid:{uid}")
            for dir in group.directory_ids:
                if dir.child_directory_ids.ids:
                    sub = True
                else:
                    sub = False
                _logger.info(f"dir:{dir}")
                if dir.is_root_directory and dir.is_template == False:
                    data = {
                            "directory_name" : dir.name,
                            "directory_id" : dir.id,
                            "is_sub" : sub,
                            "security_type" : dir.dms_security_id.selection,
                            "security" : dir.is_security_required,
                            "perm" : {
                                "perm_create":group.perm_create,
                                "perm_write":group.perm_write,
                                "perm_download":group.perm_download,
                                "perm_lock":group.perm_lock,
                                "perm_rename":group.perm_rename,
                                "perm_delete":group.perm_unlink,
                                "perm_full_admin":group.perm_full_admin

                    }
                }
                    result.append(data)
            
        return {"success":True,"directories":result}


    @http.route('/api/attachments/file-sub-directories/<int:parent_dir>', auth='none', type='json', methods=['POST'], csrf=False)
    def sub_dir_list_temp(self,parent_dir=None,**kw):
        email = kw.get('login')
        domain = [('login','=',email)]
        uid = request.env['res.users'].sudo().search(domain).id
        result = []
        uid = request.env.user.id
        sub_dirs = request.env['dms.directory'].sudo().search([('is_root_directory','=',False),('parent_id','=',parent_dir)])
        for sub_dir in sub_dirs:
            if sub_dir.child_directory_ids.ids:
                sub = True
            else:
                sub = False
            data = {
                    "directory_name" : sub_dir.name,
                    "directory_id" : sub_dir.id,
                    "is_sub" : sub,
                    }
            result.append(data)
        return {"success":True,"directories":result}


    @http.route('/api/attachments/upload-file-temp', type='json', auth='user', methods=['POST'])
    def upload_file_temp(self, **post):
        email = post.get('login')
        domain = [('login','=',email)]
        uid = request.env['res.users'].sudo().search(domain)
        current_time = int(post.get('current_time'))
        document_status = post.get('document_status')
        upload_flag = True
        if document_status == "In Process":
            document_status = "in_process"
        if not uid :
            error_message = {'success': False,'error': 'User not exist'}
            return werkzeug.exceptions.abort(Response(json.dumps(error_message), status=404))
    # # Get the base64 string from the POST data
        file_data = post.get('file_data')
        file_name = post.get('file_name')
        directory_id = post.get('directory_id')
        directory_storage = request.env['dms.directory'].sudo().search([('id','=',directory_id)]).storage_id.id
        if not file_data or not file_name or not directory_id:
            error_message = {'success': False,'error': 'No file provided'}
            return werkzeug.exceptions.abort(Response(json.dumps(error_message), status=404))
        # Decode the base64 string
        file_content = base64.b64decode(file_data)
        # create a dms.file record 
        file = request.env['dms.file'].sudo().create({
            "name" : file_name,
            'directory_id': directory_id,
            'is_uploaded': upload_flag,
            'content' : base64.b64encode(file_content),
            'create_uid' :  uid.id,
            'storage_id' : directory_storage,
            'current_time_seconds': current_time,
            'company_id': uid.company_id.id,
            "document_status" : document_status

        })
        print(file)
        return {'success': True,
        'message': 'File uploaded successfully',
        'file': file.name,
        'id':file.id}
        
       
    @http.route('/api/attachments/update-file-status', type='json', auth='none', methods=['POST'])
    def update_document_status(self, **post):
        file_id = post.get('file_id')
        document_status = post.get('document_status')
        current_time_seconds = post.get('current_time_seconds',False)
        sha512_hash = post.get('sha512_hash',False)
        if document_status == "In Process":
            document_status = "in_process"
        if document_status == "Pending Owner":
            document_status = "pending_owner"
        file = request.env['dms.file'].sudo().search([('id','=',file_id)])
        if not file_id:
                error_message = {'success': False,'error': 'No file provided'}
                return werkzeug.exceptions.abort(Response(json.dumps(error_message), status=404))
        if not sha512_hash or not current_time_seconds:
            file.write({
            'document_status':document_status
            
            })
        else:
            file.write({
                'document_status':document_status,
                'sha512_hash':sha512_hash,
                'current_time_seconds':current_time_seconds
                })

        return {'success': True,
            'message': f'File status updated to {document_status}',
            'file': file.name}

    @http.route('/notification/post',auth='none',website=False,type='json',methods=['POST'])
    def activity(self, **kw):
        try:
            user_id = http.request.env['res.users'].sudo().search([('login','=',kw["login"])]).id
            model_id = http.request.env['ir.model'].sudo()._get(kw["model_name"]).id
            record_id = kw.get('file_id',1)
            activiy_type = http.request.env['mail.activity.type'].sudo().search([('id','=',4)])
            data = {'activity_type_id': activiy_type.id,
                "summary":kw["message"],
                "user_id": user_id,
                "res_id": record_id,  # ID of the record the activity is related to
                "res_model_id": model_id,
                "date_deadline": fields.Date.today() + timedelta(days=1),}
            activity = http.request.env['mail.activity'].sudo().create(data)
            kw.update({'activity':activity.id})
            kw.update({'User':user_id})  
            return kw
        except:
            massage = "{error':{'massage':'Something want wrong'}}"
            return werkzeug.exceptions.abort(Response(massage,status=400)) 
