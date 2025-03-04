# -*- coding: utf-8 -*-
# from odoo import http


# class MultiFolderDms(http.Controller):
#     @http.route('/multi_folder_dms/multi_folder_dms', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/multi_folder_dms/multi_folder_dms/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('multi_folder_dms.listing', {
#             'root': '/multi_folder_dms/multi_folder_dms',
#             'objects': http.request.env['multi_folder_dms.multi_folder_dms'].search([]),
#         })

#     @http.route('/multi_folder_dms/multi_folder_dms/objects/<model("multi_folder_dms.multi_folder_dms"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('multi_folder_dms.object', {
#             'object': obj
#         })

