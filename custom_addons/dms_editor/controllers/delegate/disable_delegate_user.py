from odoo import http
from odoo.http import request, Response
import json
import logging
from odoo.addons.dms_editor.services.email_template import mail_data

_logger = logging.getLogger(__name__)

class DisableDelegateUserController(http.Controller):
    @http.route('/api/user/disable-delegate', type='http', auth='user', methods=['POST'], csrf=False)
    def disable_delegate_user(self, **kwargs):
        """
        Disable the delegate user for the current user.

        :return: JSON response indicating success or failure.
        """
        try:
            
            # Get the current user
            current_user = request.env.user
            user_id = current_user.id
            user_email = current_user.email

            # Fetch the delegate user record
            delegate_user = request.env['sign.delegate'].sudo().search([
                ('user_id', '=', user_id)
            ], limit=1)

            if delegate_user:
                # Check for in-process sign requests
                in_process_count = request.env['document.sign'].sudo().search_count([
                    ('email', '=', user_email),
                    ('delegate_email', '=', delegate_user.delegate_email),
                    ('status', 'in', ['Draft', 'Pending'])
                ])

                if in_process_count:
                    # Delegate user has in-process sign requests
                    return Response(
                        json.dumps({
                            "success": False,
                            "message": "Delegate User is in process with sign requests."
                        }),
                        headers={'Content-Type': 'application/json'},
                        status=200
                    )

                mail_data(email_type='delegate',subject='Filesdna - Disable Delegate', email_to=delegate_user.delegate_email, header=f"You have been removed as delegate user for {current_user.name}", description="")
                # Delete the delegate user record
                delegate_user.unlink()

                return Response(
                    json.dumps({
                        "success": True,
                        "message": "Delegate User has been deleted successfully."
                    }),
                    headers={'Content-Type': 'application/json'},
                    status=200
                )

            # No delegate user found
            return Response(
                json.dumps({
                    "success": True,
                    "data": {}
                }),
                headers={'Content-Type': 'application/json'},
                status=200
            )

        except Exception as e:
            _logger.error(f"Error disabling delegate user: {str(e)}")
            return Response(
                json.dumps({
                    "success": False,
                    "message": f"An error occurred: {str(e)}"
                }),
                headers={'Content-Type': 'application/json'},
                status=500
            )
