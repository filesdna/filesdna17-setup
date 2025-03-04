from odoo import http
from odoo.http import request, Response
import json
import logging
import requests

_logger = logging.getLogger(__name__)

class UserVerificationController(http.Controller):

    @http.route('/api/liveness/enroll', type='http', auth='user', methods=['POST'], csrf=False)
    def enroll_user(self, **kwargs):
        try:
            request_data = json.loads(request.httprequest.data.decode('utf-8'))
            # Get user information
            user = request.env.user
            user_id = user.id
            email = user.email

            # Get input data
            image = request_data.get('image', '')
            if not image:
                return self._response_error("Image is required.")

            # Check if the user exists in the database
            user_data = request.env['user.verification'].sudo().search([('user_id', '=', user_id)], limit=1)
            if not user_data:
                return self._response_error("User not found")

            # Enroll user using external API
            enroll_response = self._enroll_user_api(email, image)
            if enroll_response.get('success'):
                # Update user's liveness verification status to 1
                user_data.sudo().write({'is_verify_liveness': 1})
                return self._response_success(enroll_response)
            else:
                return self._response_error(enroll_response.get('message', "Failed to enroll user"))

        except Exception as e:
            _logger.error(f"Error in enroll_user: {str(e)}")
            return self._response_error("An error occurred while enrolling the user.")

    def _enroll_user_api(self, name, image):
        """
        Enroll user using external API.
        """
        try:
            url = "https://liveness-europe.filesdna.com/enroll_user"
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
            }
            payload = {"name": name, "image": image}
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                return {"success": True, **data}
            else:
                return {"success": False, "message": response.text}
        except Exception as e:
            _logger.error(f"Error enrolling user with external API: {str(e)}")
            return {"success": False, "message": str(e)}

    def _response_success(self, data):
        """
        Success response
        """
        return Response(
            json.dumps({"success": True, "data": data}),
            headers={'Content-Type': 'application/json'},
            status=200
        )

    def _response_error(self, message, status=400):
        """
        Error response
        """
        return Response(
            json.dumps({"success": False, "message": message}),
            headers={'Content-Type': 'application/json'},
            status=status
        )
