# -*- coding: utf-8 -*-
# from odoo import http


# class ProjectFeatures(http.Controller):
#     @http.route('/project_features/project_features', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/project_features/project_features/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('project_features.listing', {
#             'root': '/project_features/project_features',
#             'objects': http.request.env['project_features.project_features'].search([]),
#         })

#     @http.route('/project_features/project_features/objects/<model("project_features.project_features"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('project_features.object', {
#             'object': obj
#         })

