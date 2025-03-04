# -*- coding: utf-8 -*-
# from odoo import http


# class UsersPanel(http.Controller):
#     @http.route('/users_panel/users_panel', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/users_panel/users_panel/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('users_panel.listing', {
#             'root': '/users_panel/users_panel',
#             'objects': http.request.env['users_panel.users_panel'].search([]),
#         })

#     @http.route('/users_panel/users_panel/objects/<model("users_panel.users_panel"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('users_panel.object', {
#             'object': obj
#         })

