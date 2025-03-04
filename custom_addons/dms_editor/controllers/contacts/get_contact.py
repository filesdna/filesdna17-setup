import logging
import json
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

class ContactController(http.Controller):

    @http.route('/api/contact/get-contact', type='http', auth='user', methods=['GET'], csrf=False)
    def get_contact(self, **kwargs):
        try:
            user = request.env.user

            # Validate user
            if not user:
                return Response(
                    json.dumps({'message': "Invalid User", 'success': False}),
                    status=400,
                    mimetype='application/json'
                )

            # Extract inputs
            contact_type = kwargs.get('type', 'contact')

            # Query contacts based on criteria
            records = request.env['res.partner'].sudo().search([('active', '=', True),('email','!=', False)])

            # Prepare response data with selected fields and is_guest status
            data = []
            for rec in records:
                # Serialize record data with only necessary fields
                record_data = {
                    'id': rec.id,
                    'first_name': rec.name,
                    'last_name': "",  # Assuming empty string if not provided
                    'email': rec.email,
                    'phone_number': rec.phone,
                    'country': rec.country_id.name if rec.country_id else None,
                    'company_name': rec.company_registry,
                    'department': None,  # Assuming department is None
                    'is_guest': request.env['res.users'].sudo().search_count([('email', '=', rec.email)]) == 0,
                    'user_id': request.env['res.users'].sudo().search([('partner_id', '=', rec.id)], limit=1).id,
                }
                data.append(record_data)

            response_data = {
                'data': data,
                'success': True,
            }

            return Response(json.dumps(response_data), status=200, mimetype='application/json')

        except Exception as e:
            _logger.error(f"Error retrieving contact data: {str(e)}")
            return Response(
                json.dumps({'success': False, 'message': "An error occurred while processing your request."}),
                status=500,
                mimetype='application/json'
            )
