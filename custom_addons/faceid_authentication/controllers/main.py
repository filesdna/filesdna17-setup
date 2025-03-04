import json
import logging

import odoo
import odoo.modules.registry
from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.service import security
from odoo.tools import ustr
from odoo.tools.translate import _
from odoo.addons.web.controllers.utils import ensure_db

_logger = logging.getLogger(__name__)

class FaceidAuthentication(http.Controller):
    @http.route('/faceid_authentication/_get_human_config_params', type='json', auth='public', website=True)
    def _get_human_config_params(self):
        human_backend = request.env['ir.config_parameter'].sudo().get_param('faceid_authentication.human_backend')
        human_similarity = request.env['ir.config_parameter'].sudo().get_param('faceid_authentication.human_similarity')
        human_blinkdetection = request.env['ir.config_parameter'].sudo().get_param('faceid_authentication.human_blinkdetection')
        human_facingcenter = request.env['ir.config_parameter'].sudo().get_param('faceid_authentication.human_facingcenter')
        human_lookingcenter = request.env['ir.config_parameter'].sudo().get_param('faceid_authentication.human_lookingcenter')
        human_antispoofcheck = request.env['ir.config_parameter'].sudo().get_param('faceid_authentication.human_antispoofcheck')
        human_livenesscheck = request.env['ir.config_parameter'].sudo().get_param('faceid_authentication.human_livenesscheck')

        return {
            'human_backend': human_backend or 'webgl',
            'human_similarity': human_similarity or 55,
            'human_blinkdetection': human_blinkdetection or False,
            'human_facingcenter': human_facingcenter or False,
            'human_lookingcenter': human_lookingcenter or False,
            'human_antispoofcheck': human_antispoofcheck or False,
            'human_livenesscheck': human_livenesscheck or False,
        }
    
    def _login_redirect(self, uid, redirect=None):
        return redirect if redirect else '/web'
        
    @http.route('/web/login/faceid_auth', type='json', auth="none")
    def web_login_faceid_auth(self, redirect=None, **kw):
        ensure_db()
        request.params['login_success'] = False
        if not request.uid:
            request.update_env(user=odoo.SUPERUSER_ID)

        
        values = request.params.copy()
        try:
            values['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            values['databases'] = None
        
        old_uid = request.uid
        user = request.env['res.users.faces'].sudo().search([
            ('id', '=', request.params['descriptor_id']),
            ('login', '=', request.params['login'])
            ], limit=1).user_id
        try:            
            if user:
                uid = request.session.authenticate_with_faceid(request.session.db,user.id)
                values['login_success'] = True
                redirect = self._login_redirect(uid, redirect=redirect)
                values['url'] = redirect                
            else:
                return False
        except odoo.exceptions.AccessDenied as e:
            request.uid = old_uid
            if e.args == odoo.exceptions.AccessDenied().args:
                values['error'] = _("Wrong login/password")
            else:
                values['error'] = e.args[0]
        if not odoo.tools.config['list_db']:
            values['disable_database_manager'] = True

        if 'login' not in values and request.session.get('auth_login'):
            values['login'] = request.session.get('auth_login')

        if 'debug' in values:
            values['debug'] = True

        return values
    
    @http.route('/faceid_authentication/loadLabeledImages/', type='json', auth="none")
    def load_labeled_images(self):
        descriptions = []
        users = request.env['res.users'].sudo().search([])
        for user in users:
            descriptors = []
            for faces in user.user_faces:
                if faces.descriptor and faces.descriptor != 'false':
                    descriptors.append({
                        'descriptor_id': faces.id ,
                        'descriptor': faces.descriptor,
                    })
            if descriptors:
                vals = {
                    "label": user.id,
                    "descriptors": descriptors,
                    "name": user.name,
                    'login': user.login,
                }
                descriptions.append(vals)
        return descriptions

    @http.route('/faceid_authentication/getName/<int:user_id>/', type='json', auth="none")
    def get_name(self,user_id):
        name = False
        if user_id:
            user = request.env['res.users'].sudo().search([('id', '=', int(user_id))])
            name =  user.name
        return name