from odoo import http
from odoo.http import request, Response
from datetime import datetime, date
import json
import hashlib
import base64
from odoo.addons.dms_editor.services.signature import SignatureHelper
from odoo.addons.dms_editor.services.user import User
from odoo.tools import config
import logging

_logger = logging.getLogger(__name__)

# Services
signature = SignatureHelper()
user = User()

server_path = config['server_path']

class UpdateUserSignatureController(http.Controller):
    @http.route('/api/user/update-signature', type='http', auth='user', methods=['POST'], csrf=False)
    def update_signature(self, **kwargs):
        """
        Update a user signature.

        :param kwargs: JSON payload with signature details.
        :return: JSON response indicating success or failure.
        """
        try:
            request_data = json.loads(request.httprequest.data.decode('utf-8'))
            inputs = request_data

            # Validate inputs
            if not inputs.get('signature_id') or not inputs.get('type'):
                return self._response_error("Missing required fields: signature_id or type.")

            # Get current user details
            current_user = request.env.user
            user_id = current_user.id

            # Fetch the existing signature
            signature_record = request.env['user.signature'].sudo().search([
                ('id', '=', inputs['signature_id']),
                ('user_id', '=', user_id)
            ], limit=1)

            if not signature_record:
                return self._response_error("No signature found.")

            inputs['sign_by'] = current_user.name
            inputs['date']

            updated_data = {}

            # Update based on the signature type
            if inputs['type'] == 'choose':
                # Generate new full signature
                signature_font = f"sign{inputs.get('signature_font')}" if inputs.get('signature_font') != "roboto" else "roboto"

                full_signature = signature.upload_signature(
                    name=inputs.get('full_name', current_user.name),
                    font_path=f"{server_path}/dms_editor/static/src/fonts/{signature_font}.ttf",
                    sign_type="full",
                    sign_by=inputs['sign_by'],
                    date=inputs['date'],
                    reason=inputs.get('reason', ""),
                    no_design='0' if inputs.get('no_design') else '1',
                    base64_output=False
                )

                initial_signature = signature.upload_signature(
                    name=inputs.get('initial_name', current_user.name),
                    font_path=f"{server_path}/dms_editor/static/src/fonts/{signature_font}.ttf",
                    sign_type="initial",
                    sign_by="",
                    date="",
                    reason="",
                    no_design= '0' if inputs.get('no_design') else '1',
                    base64_output=False
                )

                if full_signature.get('image'):
                    signature.remove_old_signature(signature_record.full_signature, "choose")
                    updated_data['full_signature'] = full_signature['image']
                    updated_data['signature_hash'] = full_signature['hash']

                if initial_signature.get('image'):
                    signature.remove_old_signature(signature_record.initial_signature, "choose")
                    updated_data['initial_signature'] = initial_signature['image']

            elif inputs['type'] in ['draw', 'upload']:
                # Update full signature
                if inputs.get('signature'):
                    signature.remove_old_signature(signature_record.full_signature, inputs['type'])
                    hash_key = hashlib.sha512(inputs['signature'].encode()).hexdigest()[:11]

                    base64_full = signature.generate_html_signature_base64(
                        inputs['signature'],
                        hash_key,
                        "full",
                        inputs['sign_by'],
                        inputs['date'],
                        inputs.get('reason', ""),
                        '0' if inputs.get('no_design') else '1'
                    )

                    uploaded_full = user.upload_file(base64_full, "signature")
                    updated_data['full_signature'] = uploaded_full
                    updated_data['signature_hash'] = hash_key

                # Update initial signature
                if inputs.get('initial'):
                    signature.remove_old_signature(signature_record.initial_signature)
                    base64_initial = signature.generate_html_signature_base64(
                        inputs['initial'],
                        "",
                        "initial",
                        "",
                        "",
                        "",
                        '0' if inputs.get('no_design') else '1'
                    )

                    uploaded_initial = user.upload_file(base64_initial, "signature")
                    updated_data['initial_signature'] = uploaded_initial

            # Update signature record in database
            updated_data.update({
                'full_name': inputs.get('full_name'),
                'initial_name': inputs.get('initial_name'),
                'signature_font': inputs.get('signature_font'),
                'type': inputs['type'],
                'sign_by': inputs['sign_by'],
                'date': inputs['date'],
                'reason': inputs.get('reason', ""),
                'no_design': '0' if inputs.get('no_design') else '1'
            })

            signature_record.sudo().write(updated_data)

            return self._response_success("Signature has been updated successfully.", signature_record)

        except Exception as e:
            _logger.error(f"Error updating signature: {str(e)}")
            return self._response_error(f"An error occurred: {str(e)}")

    def _response_error(self, message, status=400):
        return Response(
            json.dumps({"message": message, "success": False}),
            headers={'Content-Type': 'application/json'},
            status=status
        )

    def _response_success(self, message, record):
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
                "message": message,
                "data": serialized_data,
                "success": True
            }),
            headers={'Content-Type': 'application/json'},
            status=200
        )