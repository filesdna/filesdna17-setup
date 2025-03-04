import logging
import json
from odoo import http
from odoo.http import request, Response
from odoo.addons.dms_editor.services.helpers import serialize_record

_logger = logging.getLogger(__name__)

class ContactController(http.Controller):

    @http.route('/api/contact/create', type='http', auth='user', methods=['POST'], csrf=False)
    def create_contact(self, **kwargs):
        try:
            user = request.env.user
            user_id = user.id
            current_email = user.email.lower()
            
            # Extract inputs
            first_name = kwargs.get('first_name')
            last_name = kwargs.get('last_name', "")
            email = kwargs.get('email').lower()
            phone_number = kwargs.get('phone_number')

            if email == current_email:
                return Response(
                    json.dumps({
                        "message": "You cannot add your own email",
                        "success": False,
                    }),
                    status=200,
                    mimetype='application/json'
                )

            # Check for existing contact
            existing_contact = request.env['res.partner'].sudo().search_count([('email', '=', email), ('active', '=', True)])
            if existing_contact:
                return Response(
                    json.dumps({
                        "message": "Contact already exists",
                        "success": False,
                    }),
                    status=200,
                    mimetype='application/json'
                )

            # Create contact
            contact_vals = {
                'name': first_name,
                'email': email,
                'mobile': phone_number,
                'phone': phone_number,
            }
            new_contact = request.env['res.partner'].sudo().create(contact_vals)

            # Check if delegate exists for contact
            delegate = request.env['sign.delegate'].sudo().search([('email', '=', email)], limit=1)
            if delegate:
                new_contact.delegate_user = delegate

            # Log audit event
            # ip_address = request.httprequest.remote_addr
            # audit_message = f"You added contact <b>{first_name}</b> from IP: <b>{ip_address}</b>"

            # request.env['audit.log'].sudo().create({
            #     'user_id': user_id,
            #     'message': audit_message,
            #     'model': 'res.partner',
            #     'event_type': 'contact_addition',
            #     'date': fields.Datetime.now(),
            #     'additional_info': "",
            #     'is_free_plan': plan.is_free,
            # })
            

            return Response(
                json.dumps({
                    "message": "Contact has been added!",
                    "success": True,
                }),
                status=200,
                mimetype='application/json'
            )

        except Exception as e:
            _logger.error(f"Error creating contact: {str(e)}")
            return Response(
                json.dumps({
                    "success": False,
                    "message": "An error occurred while processing your request.",
                }),
                status=500,
                mimetype='application/json'
            )
