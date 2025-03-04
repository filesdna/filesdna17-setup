from odoo import http
from odoo.http import request, Response
import json
import logging

_logger = logging.getLogger(__name__)

class UserBlockchainDetailsController(http.Controller):
    @http.route('/api/user/get-user-bc-details', type='http', auth='user', methods=['POST'], csrf=False)
    def get_user_bc_details(self, **kwargs):
        try:
            # Retrieve the current user from the request
            user = request.env.user

            if user:
                # Fetch blockchain account details for the user
                user_details = request.env['res.users'].sudo().search_read(
                    [('id', '=', user.id)],
                    fields=['blockchain_uid', 'bc_account'],
                    limit=1
                )

                if user_details:
                    return Response(
                        json.dumps({
                            "success": True,
                            "data": {
                                "bc_account": json.loads(user_details[0]['bc_account'].replace("'",'"')),
                                "id" :user_details[0]['blockchain_uid']
                            }
                        }),
                        headers={'Content-Type': 'application/json'},
                        status=200
                    )
                else:
                    return Response(
                        json.dumps({
                            "success": False,
                            "message": "No blockchain account details found."
                        }),
                        headers={'Content-Type': 'application/json'},
                        status=404
                    )
            else:
                return Response(
                    json.dumps({
                        "success": False,
                        "message": "Invalid user."
                    }),
                    headers={'Content-Type': 'application/json'},
                    status=401
                )
        except Exception as e:
            _logger.error(f"Error fetching user blockchain details: {str(e)}")
            return Response(
                json.dumps({
                    "success": False,
                    "message": "An error occurred while processing the request."
                }),
                headers={'Content-Type': 'application/json'},
                status=500
            )
