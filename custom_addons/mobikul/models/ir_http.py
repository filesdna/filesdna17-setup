# -*- coding: utf-8 -*-
##########################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
##########################################################################
from odoo import api, models
from odoo.http import request


from odoo.addons.web.controllers.binary import Binary
import logging
_logger = logging.getLogger(__name__)

from odoo import http, _
from odoo.http import request

class Binary(Binary):
    @http.route()
    def content_image(self, xmlid=None, model='ir.attachment', id=None, field='raw',
                      filename_field='name', filename=None, mimetype=None, unique=False,
                      download=False, width=0, height=0, crop=False, access_token=None,
                      nocache=False):
        env = request.env
        obj = None
        if xmlid:
            obj = env.ref(xmlid, False)
        elif id and model in env:
            obj = env[model].browse(int(id))
        # if obj and 'is_mobikul_available' in obj._fields:
        #     if env[obj._name].sudo().search([('id', '=', obj.id), ('is_mobikul_available', '=', True)]):
        #         self = self.sudo()
        #         pass
        if obj and obj._name == "res.partner" and field in ("image_1920", "profile_banner", "profile_image", "banner_image"):
            request.update_env(user=request.env['res.users'].sudo().browse(1))
        res = super(Binary, self).content_image(xmlid=xmlid, model=model, id=id, field=field,
                      filename_field=filename_field, filename=filename, mimetype=mimetype, unique=unique,
                      download=download, width=width, height=height, crop=crop, access_token=access_token,
                      nocache=nocache)
        return res
