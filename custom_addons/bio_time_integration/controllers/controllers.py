# -*- coding: utf-8# -*- coding: utf-8 -*-
from odoo import http

import werkzeug.exceptions
from odoo.http import Response
from datetime import date, datetime, timedelta


class RestAPIBioTimePost(http.Controller):
    @http.route('/api/post_attendance_transactions',auth='public',website=False,type='json',csrf=False,methods=['POST'])
    def index(self, **kw):
        exist_record_id = http.request.env['hr.attendance.bio'].sudo().search([('record_id','=',kw['id'])]).id
        if exist_record_id == False:
            date_string = kw['punch_time']
            date_format = "%Y-%m-%d %H:%M:%S"
            punch_time = datetime.strptime(date_string, date_format)
            punch_time = punch_time - timedelta(hours=4)
            http.request.env['hr.attendance.bio'].sudo().create({
                'name': http.request.env['hr.employee'].sudo().search([('device_id','=',kw['emp_code'])]).id,
                'record_id':kw['id'],
                'punching_day':kw['upload_time'],
                'punch_time':punch_time,
                'attendance_type':str(kw['verify_type']),
                'punch_type':str(kw['punch_state']),
                'device_id':str(kw['terminal_alias']),
                'seq_num':str(kw['terminal_sn'])
                })    
        return kw

            
        #     massage = "{error':{'massage':''}}"
        #     return werkzeug.exceptions.abort(Response(massage,status=400))  
