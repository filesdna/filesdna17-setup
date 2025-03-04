from odoo import http
from odoo.http import request, Response
import json
from odoo.tools import config
from odoo.addons.dms_editor.services.google_storage import LocalStorageService
from datetime import datetime, date
 
server_path = config['server_path']

class UserSignatureController(http.Controller):
    @http.route('/api/user/get-signature', type='http', auth='user', methods=['GET'], csrf=False)
    def get_signature(self, **kwargs):
        """
        Retrieve user signatures.

        :return: JSON response with user signature data.
        """
        try:
            gcs = LocalStorageService()

            # Get the current user
            user = request.env.user
            if not user:
                return Response(
                    json.dumps({"message": "Invalid User", "success": False}),
                    headers={'Content-Type': 'application/json'},
                    status=400
                )

            # Fetch user signature records
            user_signatures = request.env['user.signature'].sudo().search_read(
                domain=[('user_id', '=', user.id)],
                fields=[
                    "full_name", "initial_name", "full_signature", "initial_signature",
                    "type", "default", "date", "reason", "sign_by", "signature_font",
                    "no_design", "initial", "signature"
                ],
                order="default desc"
            )

            # Process signatures for file URLs and convert datetime to strings, default/no_design to int
            def serialize_record(record):
                for key, value in record.items():
                    if isinstance(value, (datetime, date)):
                        record[key] = value.isoformat()  # Convert datetime to ISO 8601 format
                    elif key in ["default", "no_design"]:  # Explicit conversion to int
                        record[key] = int(value) if value is not None else 0
                return record

            processed_signatures = []
            for record in user_signatures:
                if record.get('full_signature'):
                    record['full_signature'] = gcs.read_url(record['full_signature'])
                if record.get('initial_signature'):
                    record['initial_signature'] = gcs.read_url(record['initial_signature'])
                processed_signatures.append(serialize_record(record))

            # Return processed data
            return Response(
                json.dumps({"data": processed_signatures, "success": True}),
                headers={'Content-Type': 'application/json'},
                status=200
            )

        except Exception as e:
            return Response(
                json.dumps({"message": f"An error occurred: {str(e)}", "success": False}),
                headers={'Content-Type': 'application/json'},
                status=500
            )
