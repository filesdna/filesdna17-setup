# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.http import Response
import json
import logging

_logger = logging.getLogger(__name__)

class FirebaseFCM(http.Controller):

    @http.route('/user/fcm', auth='user', website=False, type='json', csrf=False, methods=['POST'])
    def update_fcm(self, **kw):
        try:
            uid = request.env.user
            fcm_token = kw.get('fcm_token')
            if not fcm_token:
                return Response(json.dumps({"success": False, "message": "FCM token is missing"}), status=400, mimetype='application/json')

            uid.sudo().write({
                "firebase_token": fcm_token
            })
            _logger.info("FCM token for user %s has been updated to %s", uid.login, uid.firebase_token)
            message = {"success": True, "message": f"FCM for {uid.login} has been updated"}
            return Response(json.dumps(message), status=200, mimetype='application/json')
        except Exception as e:
            _logger.error("Error updating FCM token: %s", str(e))
            return Response(json.dumps({"success": False, "message": "An error occurred while updating FCM token"}), status=500, mimetype='application/json')

    @http.route('/user/fcm/check_status', auth='user', website=False, type='json', csrf=False, methods=['POST'])
    def get_fcm(self, **kw):
        uid = request.env.user.id
        status = kw.get('status')
        security_type = kw.get('type')
        security_record = request.env['dms.security'].search(
            [('user_id','=',uid),
            ('selection','=',security_type)])
        if security_record:
            security_record.is_required = status
            security_record.notification_status = "delivered"
            return {'success':True}
        else:
            return {'success':False}
    
    @http.route('/user/fcm/dms_security/check_notification_status', type='json', auth='user')
    def check_dmssecurity_status(self, record_id):
        record = request.env['dms.security'].browse(record_id)
        return {'success':True,
        'notification_status': record.notification_status,
        'security_type' : record.selection,
        'uid' : record.user_id.id
        }
   
    

    @http.route('/user/fcm/notification_status', auth='user', website=False, type='json', csrf=False, methods=['POST'])
    def get_fcm_status(self, **kw):
        status = kw.get('status')
        file_id = kw.get('file_id')
        file_record = request.env['dms.file'].search([('id','=',file_id)])
        file_record.notification_status = status
        return {'success':True}
    
    @http.route('/user/fcm/check_notification_status', type='json', auth='user')
    def check_notification_status(self, record_id):
        record = request.env['dms.file'].browse(record_id)
        return {'success':True,
        'notification_status': record.notification_status,
        'security_type' : record.dms_security_id.selection
        }
   