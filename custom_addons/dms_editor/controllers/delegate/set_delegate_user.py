from odoo import http
from odoo.http import request, Response
from datetime import datetime, date
import json
import logging
from odoo.addons.dms_editor.services.email_template import mail_data

_logger = logging.getLogger(__name__)


class SignDelegationController(http.Controller):
    @http.route('/api/user/set-delegate-user', type='http', auth='user', methods=['POST'], csrf=False)
    def set_delegation(self, **kwargs):
        """
        Set delegation for a user to another delegate for signing.

        :param kwargs: JSON payload containing email, first_name, last_name, start_date, and end_date.
        :return: JSON response indicating success or failure.
        """
        try:
            request_data = json.loads(request.httprequest.data.decode('utf-8'))

            # Extract input data
            email = request_data.get('email', '').lower()
            first_name = request_data.get('first_name')
            last_name = request_data.get('last_name', '')
            start_date = request_data.get('start_date')
            end_date = request_data.get('end_date')

            # Validate input
            if not email or not first_name or not start_date or not end_date:
                return self._response_error("Missing required fields.")

            current_user = request.env.user
            user_id = current_user.id

            # Convert date strings to datetime objects
            try:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                return self._response_error("Invalid date format. Use YYYY-MM-DD.")

            # Check if delegation already exists
            sign_delegate_model = request.env['sign.delegate'].sudo()
            existing_delegate = sign_delegate_model.search([('user_id', '=', user_id)], limit=1)

            if existing_delegate:
                # Update the existing delegation record
                existing_delegate.write({
                    'email': current_user.email,
                    'delegate_email': email,
                    'delegate_first_name': first_name,
                    'delegate_last_name': last_name,
                    'start_date': start_date_obj,
                    'end_date': end_date_obj,
                    'is_active': '1',
                })
                response_message = "Delegate User has been updated successfully."
            else:
                # Create a new delegation record
                new_delegate = sign_delegate_model.create({
                    'user_id': user_id,
                    'email': current_user.email,
                    'delegate_email': email,
                    'delegate_first_name': first_name,
                    'delegate_last_name': last_name,
                    'start_date': start_date_obj,
                    'end_date': end_date_obj,
                    'is_active': '1',
                })
                existing_delegate = new_delegate
                response_message = "Delegate User has been added successfully."

            # Format dates for response
            result_data = {
                "id": existing_delegate.id,
                "delegate_email": existing_delegate.delegate_email,
                "delegate_first_name": existing_delegate.delegate_first_name,
                "delegate_last_name": existing_delegate.delegate_last_name,
                "start_date": existing_delegate.start_date.strftime("%d-%m-%Y"),
                "end_date": existing_delegate.end_date.strftime("%d-%m-%Y"),
                "is_active": '1' if existing_delegate.is_active else '0',
            }

            mail_data(email_type='delegate',subject='Filesdna - Set Delegate', email_to=email, header=f"You have been added as delegate user for {current_user.name}", description=f"You have been added as delegate user for {current_user.name}. start date:{start_date} - end date:{end_date}")

            # Success response
            return self._response_success(response_message, result_data)

        except Exception as e:
            _logger.error(f"Error in set_delegation: {str(e)}")
            return self._response_error(f"An error occurred: {str(e)}")

    def _response_error(self, message, status=400):
        """Helper method to return error response."""
        return Response(
            json.dumps({"message": message, "success": False}),
            headers={'Content-Type': 'application/json'},
            status=status
        )

    def _response_success(self, message, data):
        """Helper method to return success response."""
        def serialize_record(data):
            """
            Convert datetime fields to ISO format strings.
            """
            for key, value in data.items():
                if isinstance(value, (datetime, date)):
                    data[key] = value.isoformat()  # Convert datetime to ISO 8601 format
            return data
        record_data = data
        serialized_data = serialize_record(record_data)  # Convert datetime fields
        
        return Response(
            json.dumps({"message": message, "data": serialized_data, "success": True}),
            headers={'Content-Type': 'application/json'},
            status=200
        )
