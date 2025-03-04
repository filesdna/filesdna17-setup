import logging
import json
import os
import base64
from datetime import datetime
from odoo import http
from odoo.http import request, Response
from odoo.addons.dms_editor.services.google_storage import LocalStorageService
from odoo.tools import config

_logger = logging.getLogger(__name__)

# Configuration
 
server_path = config['server_path']

class VoiceEnrollController(http.Controller):

    @http.route('/api/file/save-sign-security', type='http', auth='public', methods=['POST'], csrf=False)
    def enroll_master_voice(self, **kwargs):
        try:
            # Parse input parameters
            hash_key = kwargs.get('hash')
            voice_code = kwargs.get('voice_code')
            user = request.env.user

            # Validate inputs
            if not hash_key or not voice_code:
                return self._response_error("Missing required parameters.")

            # Fetch document sign based on the hash
            check_hash = request.env['document.sign'].sudo().search([
                ('user_hash', '=', hash_key)
            ], limit=1)

            if not check_hash:
                return self._response_error("Invalid document.")

            # Process uploaded file
            file_storage = request.httprequest.files.get('voice_file')
            if not file_storage:
                return self._response_error("No voice file provided.")

            # Save the uploaded file locally
            file_ext = file_storage.filename.split('.')[-1]
            temp_path = f'{server_path}/dms_editor/static/src/temp'
            file_name = f"{check_hash.document_id.id}-{int(datetime.now().timestamp())}.{file_ext}"
            local_file_path = os.path.join(temp_path, file_name)

            # Save the file locally
            file_storage.save(local_file_path)

            # Upload the file to Google Cloud Storage
            key_file = f"{server_path}/google_cloud_storage/google_creds.json"
            gcs_service = LocalStorageService()
            db_name= request.env['ir.config_parameter'].sudo().get_param('web.base.url').split("//")[-1].split(".")[0]
            gcs_destination = f"{db_name}/voice/{file_name}"
            upload_result = gcs_service.upload_file(local_file_path, gcs_destination, None)

            # Update document sign details
            if upload_result:
                file_url = gcs.read_url(gcs_destination)
                check_hash.sudo().write({
                    'reason': file_url,
                    'voice_code': voice_code
                })

            # Return success response
            return self._response_success("Voice enrolled successfully.")

        except Exception as e:
            _logger.error(f"Error in enroll_master_voice: {str(e)}")
            return self._response_error("An error occurred while enrolling the voice.")

    # Response error helper
    def _response_error(self, message, status=400):
        return Response(
            json.dumps({"success": False, "message": message}),
            headers={'Content-Type': 'application/json'},
            status=status
        )

    # Response success helper
    def _response_success(self, message):
        return Response(
            json.dumps({"success": True, "message": message}),
            headers={'Content-Type': 'application/json'},
            status=200
        )
