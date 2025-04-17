import logging
import json
import requests
from odoo import http
from odoo.http import request, Response
from odoo.tools import config

_logger = logging.getLogger(__name__)

class VoiceRemoveController(http.Controller):

    @http.route(['/api/voice/reset','/api/voice-non-user/reset'], type='http', auth='public', methods=['POST'], csrf=False)
    def remove_voice(self, **kwargs):
        try:
            # Parse input parameters
            token = kwargs.get('token', 'gloryvoicefootprint')  # Default token
            email = kwargs.get('email') or request.env.user.email  # Use provided email or current user's email
            user_id = request.env.user.id

            # Validate inputs
            if not email or not token:
                return self._response_error("Missing required parameters.")

            # Prepare API request to external service
            url = "https://voice1.filesdna.com/remove"
            headers = {'accept': 'application/json'}
            data = {'name': email, 'token': token}

            response = requests.post(url, headers=headers, data=data)
            response_data = response.json()
            _logger.info(f"response_data:{response_data}")
            # Update user verification status to 0
            if not kwargs.get('email'):  # Update only for the logged-in user, not for external requests
                request.env['user.verification'].sudo().search([('user_id', '=', user_id)]).write({ 'is_verify_voice': 0 })
            return self._response_success(response_data)


        except Exception as e:
            _logger.error(f"Error in remove_voice: {str(e)}")
            return self._response_error("An error occurred while removing the voice profile.")

    # Response error helper
    def _response_error(self, message, status=400):
        return Response(
            json.dumps({"success": False, "message": message}),
            headers={'Content-Type': 'application/json'},
            status=status
        )

    # Response success helper
    def _response_success(self, data):
        return Response(
            json.dumps({"success": True, "data": data}),
            headers={'Content-Type': 'application/json'},
            status=200
        )
