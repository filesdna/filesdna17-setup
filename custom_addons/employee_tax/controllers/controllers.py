# -*- coding: utf-8 -*-
# from odoo import http


# class EmployeeTax(http.Controller):
#     @http.route('/employee_tax/employee_tax', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/employee_tax/employee_tax/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('employee_tax.listing', {
#             'root': '/employee_tax/employee_tax',
#             'objects': http.request.env['employee_tax.employee_tax'].search([]),
#         })

#     @http.route('/employee_tax/employee_tax/objects/<model("employee_tax.employee_tax"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('employee_tax.object', {
#             'object': obj
#         })

