from odoo import http
from odoo.http import request, Response
import json
import logging
import requests

_logger = logging.getLogger(__name__)

class UserVerificationController(http.Controller):

    @http.route('/api/liveness/reset', type='http', auth='user', methods=['POST'], csrf=False)
    def remove_user(self, **kwargs):
        try:
            # Get user information
            user = request.env.user
            user_id = user.id
            email = user.email

            # Check if the user exists in the database
            user_data = request.env['user.verification'].sudo().search([('user_id', '=', user_id)], limit=1)
            if not user_data:
                return self._response_error("User not found")

            # Remove user using external API
            is_remove_user = self._remove_user_api(email)
            if is_remove_user.get('success'):
                # Update the user's liveness verification status to 0
                user_data.sudo().write({'is_verify_liveness': 0})
                return self._response_success(is_remove_user)
            else:
                return self._response_error(is_remove_user.get('message', "Failed to remove user"))

        except Exception as e:
            _logger.error(f"Error in remove_user: {str(e)}")
            return self._response_error("An error occurred while removing the user.")

    def _remove_user_api(self, name):
        """
        Remove user using external API.
        """
        try:
            url = "https://liveness-europe.filesdna.com/remove_user"
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
            }
            payload = {"name": name}
            response = requests.post(url, headers=headers, json=payload)
            _logger.info(f"response:{response}")
            if response.status_code == 200:
                data = response.json()
                return {"success": True, **data}
            else:
                return {"success": False, "message": response.text}
        except Exception as e:
            _logger.error(f"Error removing user with external API: {str(e)}")
            return {"success": False, "message": str(e)}

    def _response_success(self, data):
        """
        Success response
        """
        return Response(
            json.dumps(data),
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
