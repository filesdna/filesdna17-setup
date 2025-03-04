# -*- coding: utf-8 -*-
# from odoo import http


# class EmployeeMoreDetails(http.Controller):
#     @http.route('/employee_more_details/employee_more_details', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/employee_more_details/employee_more_details/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('employee_more_details.listing', {
#             'root': '/employee_more_details/employee_more_details',
#             'objects': http.request.env['employee_more_details.employee_more_details'].search([]),
#         })

#     @http.route('/employee_more_details/employee_more_details/objects/<model("employee_more_details.employee_more_details"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('employee_more_details.object', {
#             'object': obj
#         })

