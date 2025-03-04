from odoo import http
from odoo.http import request, Response
import json
import logging
from datetime import datetime, date

_logger = logging.getLogger(__name__)


class DefaultUserSignatureController(http.Controller):
    @http.route('/api/user/set-default-sign', type='http', auth='user', methods=['POST'], csrf=False)
    def set_default_signature(self, **kwargs):
        """
        Set a default signature for the user.

        :param kwargs: JSON payload containing 'signature_id'.
        :return: JSON response indicating success or failure.
        """
        try:
            request_data = json.loads(request.httprequest.data.decode('utf-8'))
            # Retrieve input parameters
            signature_id = request_data.get('signature_id')

            # Validate parameters
            if not signature_id:
                return self._response_error("Invalid Parameters")

            # Get the current user
            current_user = request.env.user

            # Reset existing default signature (if any)
            existing_default = request.env['user.signature'].sudo().search([
                ('default', '=', '1'),
                ('user_id', '=', current_user.id)
            ], limit=1)

            if existing_default:
                existing_default.sudo().write({'default': '0'})
                _logger.info(f"Previous default signature reset: ID {existing_default.id}")

            # Set the new default signature
            signature_record = request.env['user.signature'].sudo().search([
                ('id', '=', signature_id),
                ('user_id', '=', current_user.id)
            ], limit=1)

            if not signature_record:
                return self._response_error("Signature not found.")

            signature_record.sudo().write({'default': '1'})
            _logger.info(f"Signature set as default: ID {signature_record.id}")

            # Return success response
            return self._response_success("Signature has been set as default.", signature_record)

        except Exception as e:
            _logger.error(f"Error setting default signature: {str(e)}")
            return self._response_error(f"An error occurred: {str(e)}")

    def _response_error(self, message, status=400):
        """
        Generate an error response.
        """
        return Response(
            json.dumps({"success": False, "message": message, "data": {}}),
            headers={'Content-Type': 'application/json'},
            status=status
        )

    def _response_success(self, message, record):
        """
        Generate a success response with serialized data.
        """
        def serialize_record(data):
            """
            Convert datetime fields to ISO format strings.
            """
            for key, value in data.items():
                if isinstance(value, (datetime, date)):
                    data[key] = value.isoformat()  # Convert datetime to ISO 8601 format
            return data

        record_data = record.read()[0]
        serialized_data = serialize_record(record_data)  # Convert datetime fields

        return Response(
            json.dumps({
                "success": True,
                "message": message,
                "data": serialized_data
            }),
            headers={'Content-Type': 'application/json'},
            status=200
        )
