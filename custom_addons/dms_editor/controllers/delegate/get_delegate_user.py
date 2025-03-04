from odoo import http
from odoo.http import request, Response
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)

class GetDelegateUserController(http.Controller):
    @http.route('/api/user/get-delegate-user', type='http', auth='user', methods=['GET'], csrf=False)
    def get_delegate_user(self, **kwargs):
        """
        Retrieve the delegate user for the current user.

        :return: JSON response with delegate user data or empty object.
        """
        try:
            # Get the current user
            current_user = request.env.user
            user_id = current_user.id

            # Fetch delegate user record
            delegate_users = request.env['sign.delegate'].sudo().search_read(
                domain=[('user_id', '=', user_id)],
                fields=[
                    'create_date',
                    'delegate_email',
                    'delegate_first_name',
                    'delegate_last_name',
                    'start_date',
                    'end_date'
                ],
                limit=1
            )

            if delegate_users:
                delegate_user = delegate_users[0]  # Access the first record
                
                # Safely convert datetime fields to strings
                def serialize_dates(record):
                    for key in ['create_date', 'start_date', 'end_date']:
                        if key in record and record[key]:
                            record[key] = record[key].strftime("%d-%m-%Y")  # Convert to DD-MM-YYYY format
                    return record

                # Serialize the dates
                delegate_user = serialize_dates(delegate_user)

                # Check if the delegation has expired
                if delegate_user['end_date']:
                    expiration_date = datetime.strptime(delegate_user['end_date'], "%d-%m-%Y") + timedelta(days=1)
                    if datetime.now().date() > expiration_date.date():
                        request.env['sign.delegate'].sudo().search([
                            ('user_id', '=', user_id)
                        ]).unlink()
                        delegate_user = None  # Set to None if record is deleted
                        _logger.info(f"Expired delegate user record deleted for user ID {user_id}")

                # Return the processed delegate user data
                return Response(
                    json.dumps({
                        "success": True,
                        "data": delegate_user if delegate_user else {}
                    }),
                    headers={'Content-Type': 'application/json'},
                    status=200
                )

            # If no delegate user is found
            return Response(
                json.dumps({
                    "success": True,
                    "data": {}
                }),
                headers={'Content-Type': 'application/json'},
                status=200
            )

        except Exception as e:
            _logger.error(f"Error fetching delegate user: {str(e)}")
            return Response(
                json.dumps({
                    "success": False,
                    "message": f"An error occurred: {str(e)}"
                }),
                headers={'Content-Type': 'application/json'},
                status=500
            )
