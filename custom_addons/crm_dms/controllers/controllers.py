# -*- coding: utf-8 -*-
# from odoo import http


# class Lawyer(http.Controller):
#     @http.route('/lawyer/lawyer', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/lawyer/lawyer/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('lawyer.listing', {
#             'root': '/lawyer/lawyer',
#             'objects': http.request.env['lawyer.lawyer'].search([]),
#         })

#     @http.route('/lawyer/lawyer/objects/<model("lawyer.lawyer"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('lawyer.object', {
#             'object': obj
#         })

