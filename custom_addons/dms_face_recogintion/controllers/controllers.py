# -*- coding: utf-8 -*-
# from odoo import http


# class DmsFaceRecogintion(http.Controller):
#     @http.route('/dms_face_recogintion/dms_face_recogintion', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/dms_face_recogintion/dms_face_recogintion/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('dms_face_recogintion.listing', {
#             'root': '/dms_face_recogintion/dms_face_recogintion',
#             'objects': http.request.env['dms_face_recogintion.dms_face_recogintion'].search([]),
#         })

#     @http.route('/dms_face_recogintion/dms_face_recogintion/objects/<model("dms_face_recogintion.dms_face_recogintion"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('dms_face_recogintion.object', {
#             'object': obj
#         })

