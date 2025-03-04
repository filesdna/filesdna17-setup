from odoo import http
from odoo.http import request, Response
import json
import logging
import base64
import requests

_logger = logging.getLogger(__name__)

class UserVerificationController(http.Controller):

    @http.route('/api/liveness/<string:verify_type>', type='http', auth='user', methods=['POST'], csrf=False)
    def verify_user(self, verify_type, **kwargs):
        try:
            # Get request data
            request_data = json.loads(request.httprequest.data.decode('utf-8'))
            verify_type = verify_type if verify_type else 'verify'
            image = request_data.get('image', '')
            user = request.env.user
            user_id = user.id
            email = user.email

            # Get user data from Odoo model
            user_data = request.env['user.verification'].sudo().search([('user_id', '=', user_id)], limit=1)
            if not user_data:
                return self._response_error("User not found")

            # Process verification type
            if verify_type == "verify":
                # Toggle liveness verification status
                new_status = 1 if user_data.is_verify_liveness == 0 else 0
                user_data.sudo().write({'is_verify_liveness': new_status})
                return self._response_success({"success": True})

            elif verify_type == "verify-user":
                # Verify user with external API
                is_verify_user = self._verify_user(email, image)
                if is_verify_user.get('success'):
                    liveness = float(is_verify_user.get('liveness', 0))
                    # If liveness score > 0.8, update verification status
                    if liveness > 0.8 and user_data.is_verify_liveness == 0:
                        user_data.sudo().write({'is_verify_liveness': 1})
                    return self._response_success()
                else:
                    return self._response_error(is_verify_user.get('message', "Verification failed"))

            else:
                return self._response_error("Invalid verification type")

        except Exception as e:
            _logger.error(f"Error in verify_user: {str(e)}")
            return self._response_error("An error occurred during verification.")

    def _verify_user(self, name, image):
        """
        Verify user with external API.
        """
        try:
            url = "https://liveness-europe.filesdna.com/verify_user_with_name"
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
            }
            payload = {"name": name, "image": image}
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                _logger.info(f"data:{data}")
                return {"success": True, **data}
            else:
                return {"success": False, "message": response.text}
        except Exception as e:
            _logger.error(f"Error verifying user with external API: {str(e)}")
            return {"success": False, "message": str(e)}

    def _response_success(self, data):
        """
        Success response
        """
        return Response(
            json.dumps({"success": True}),
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
