from odoo import http
from odoo.http import request, Response
import json
import random
from odoo.addons.dms_editor.services.blockchain import BlockchainService

class ReactPageController(http.Controller):
    @http.route('/publicform/<string:data_path>', type='http', auth='public', website=True)
    def react_home(self, data_path, **kwargs):
        return http.request.render('smartform.view_publicform_template_home', {
            'data_path': data_path,
        })

    @http.route('/api/user_info', type='http', auth='public',methods=['GET'])
    def user_info(self):
        bc = BlockchainService()
        current_user = request.env.user
        if not current_user.blockchain_uid:
            random_string = ''.join(random.choices("0123456789abcdefghiklmnopqrstuvwxyz", k=24))
            prefix = "filesdna|"
            current_user.write({'blockchain_uid':f"{prefix}{random_string}"})
        if not current_user.bc_account:
            bc_acc = bc.create_account_in_blockchain(current_user.blockchain_uid)
            current_user.write({'bc_account': bc_acc })
        
        user_verification = request.env['user.verification'].sudo().search([('user_id','=',current_user.id)])
        if not user_verification:
            user_verification = request.env['user.verification'].sudo().create({'user_id':current_user.id})
        response = Response(
            json.dumps({
                'data':{
                'user_id': current_user.id,
                'sub': current_user.id,
                'first_name': current_user.name,
                'last_name': '',
                'email': current_user.email,
                'company_name': current_user.company_id.name,
                'user_verification':{
                    'is_verify_liveness':user_verification.is_verify_liveness,
                    'is_verify_voice':user_verification.is_verify_voice,
                },
                'is_verify_liveness':user_verification.is_verify_liveness,
                'is_verify_voice':user_verification.is_verify_voice,
                },
                'success': True
            }),
            content_type='application/json',
            status=200
        )
        return response