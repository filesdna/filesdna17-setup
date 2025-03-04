# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request, Response
import json
import logging
import werkzeug.exceptions
_logger = logging.getLogger(__name__)

class NFCCARDS(http.Controller):
    
    @http.route('/user/add-nfc', auth='user', website=False, type='json', csrf=False, methods=['POST'])
    def post_nfc_cards(self, **kw):
        # try:
        card_id = kw.get('id')
        name = kw.get('name')
        is_primary = kw.get('is_primary', False)
        uid = request.env.user.id
        card_exists = request.env['res.users.nfc'].search([
                ('card_id', '=', card_id)
            ])
        if card_exists:
            return werkzeug.exceptions.abort(Response(json.dumps({'result':{'success': False, 'message': f'The card owned by another user'}}), status=422, mimetype='application/json'))
        if not name or not card_id:
            return werkzeug.exceptions.abort(Response(json.dumps({'result':{"success": False, "message": "Card ID or name is missing"}}), status=400, mimetype='application/json'))
        
        if is_primary:
            primary_card_exists = request.env['res.users.nfc'].search_count([
                ('user_id', '=', uid),
                ('is_primary', '=', True)
            ])
            if primary_card_exists:
                return werkzeug.exceptions.abort(Response(json.dumps({'result':{'success': False, 'message': 'There is already a primary card'}}), status=422, mimetype='application/json'))

        nfc_card = request.env['res.users.nfc'].sudo().create({
            "card_id": card_id,
            "name": name,
            "is_primary": is_primary,
            'user_id': uid
        })
    
        return {"success": True, "message": "Card has been added successfully", "card_id": card_id}
 
    @http.route('/user/get-cards', auth='user', website=False, type='json', csrf=False, methods=['GET'])
    def get_nfc_cards(self):  
        uid = request.env.user.id
        if not uid:
            return werkzeug.exceptions.abort(Response(json.dumps({'result':{"success": False, "message": "User not found"}}), status=400, mimetype='application/json'))
        cards = request.env['res.users.nfc'].search_read([('user_id', '=', uid)])
        return {
            "success": True,
            "message": "Cards retrieved successfully",
            "result": cards
        }
        

    @http.route('/user/change-to-primary', auth='user', website=False, type='json', csrf=False, methods=['POST'])
    def change_primary_card(self, **post):
        uid = request.env.user.id
        card_id = post.get('card_id')
        if not uid:
            return werkzeug.exceptions.abort( Response(json.dumps({'result':{'success': False, 'message': 'User not found'}}), status=400, mimetype='application/json'))
        
        card = request.env['res.users.nfc'].search([
            ('user_id', '=', uid),
            ('card_id', '=', card_id)
        ], limit=1)

        if not card:
            return werkzeug.exceptions.abort(Response(json.dumps({'result':{'success': False, 'message': 'There is no card with this ID'}}), status=404, mimetype='application/json'))

        old_primary_card = request.env['res.users.nfc'].search([
            ('user_id', '=', uid),
            ('is_primary', '=', True)
        ], limit=1)

        if old_primary_card:
            old_primary_card.sudo().write({'is_primary': False})

        card.sudo().write({'is_primary': True})

        return {'success': True, 'message': f'Primary card changed to card with ID {card_id}'}

    @http.route('/user/delete-card', auth='user', website=False, type='json', csrf=False, methods=['POST'])
    def delete_card(self,**post):
        uid = request.env.user.id
        card_id = post.get('card_id')
        if not uid:
            return werkzeug.exceptions.abort( Response(json.dumps({'result':{'success': False, 'message': 'User not found'}}), status=404, mimetype='application/json'))
        
        card = request.env['res.users.nfc'].search([
            ('user_id', '=', uid),
            ('card_id', '=', card_id)
        ], limit=1)
        if card : 
            card.sudo().unlink()
            return {'success':True,
            "message":f"Card with {card_id} ID has been deleted"
            }
        return werkzeug.exceptions.abort( Response(json.dumps({'result':{'success': False, 'message': 'Card not found'}}), status=404, mimetype='application/json'))


    @http.route('/user/verify-card', auth='user', website=False, type='json', csrf=False, methods=['POST'])
    def virfiy_card(self,**post):
        uid = request.env.user.id
        card_id = post.get('card_id')
        if not uid:
            return werkzeug.exceptions.abort( Response(json.dumps({'result':{'success': False, 'message': 'User not found'}}), status=404, mimetype='application/json'))
        
        card = request.env['res.users.nfc'].search([
            ('user_id', '=', uid),
            ('card_id', '=', card_id),
            ('is_primary', '=', True)
        ], limit=1)
        if card : 
            return {'success':True,
            "message":f"Card with {card_id} ID is exist"
            }
        return werkzeug.exceptions.abort( Response(json.dumps({"result":{'success': False, 'message': 'Unauthorized'}}), status=403, mimetype='application/json'))       