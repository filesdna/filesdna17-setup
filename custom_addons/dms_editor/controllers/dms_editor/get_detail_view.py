from odoo import http
from odoo.http import request, Response
import os
import shutil
import json
import logging
from odoo.addons.dms_editor.services.google_storage import LocalStorageService
from odoo.tools import config
from urllib.parse import quote

_logger = logging.getLogger(__name__)
 
server_path = config['server_path']

class DocumentDetailViewController(http.Controller):
    @http.route('/api/get-detail-view/<string:hash_key>', type='http', auth='public', methods=['GET'], csrf=False)
    def get_detail_view(self, hash_key, **kwargs):
        try:
            if not hash_key:
                return self._response_error("Invalid Parameters")

            # Find the document record by hash_key
            document_load = request.env['document.load.image'].sudo().search([('hash_key', '=', hash_key)], limit=1)
            if not document_load:
                return self._response_error("No document preview found")

            # Fetch the file metadata
            file_data = request.env['dms.file'].sudo().search([('id', '=', document_load.doc_image_id.id)], limit=1)
            if not file_data:
                return self._response_error("No document found")

            # Prepare temporary file path
            temp_path = '/tmp'
            filename = file_data.attachment_id.store_fname.split('/')[1]
            file_path = os.path.join(temp_path, filename)

            # Download the file if it doesn't exist locally
            if not os.path.exists(file_path):
                key_file = f"{server_path}/google_cloud_storage/google_creds.json"
                gcs_service = LocalStorageService()
                db_name= request.env['ir.config_parameter'].sudo().get_param('web.base.url').split("//")[-1].split(".")[0]
                destination_path = f"{db_name}/{file_data.attachment_id.store_fname}"
                gcs_service.download_file(destination_path, file_path, encryption_key=None)

            pdf_path = f"/tmp/{file_data.name}"
            os.rename(file_path, pdf_path)
            return self._send_file(pdf_path)


        except Exception as e:
            _logger.error(f"Error in get_detail_view: {str(e)}")
            return self._response_error("An error occurred while processing the request")


    def _send_file(self, file_path):
        try:
            with open(file_path, 'rb') as f:
                response = request.make_response(f.read())
                response.headers['Content-Type'] = 'application/pdf'
                
                # Encode filename for Content-Disposition header
                filename = os.path.basename(file_path)
                encoded_filename = quote(filename)  # Properly encode UTF-8 characters

                # Use "inline" instead of "attachment" to view in the browser
                response.headers['Content-Disposition'] = f"inline; filename*=UTF-8''{encoded_filename}"
                return response
        except Exception as e:
            _logger.error(f"Error sending file: {str(e)}")
            return self._response_error("Error displaying file")

    def _response_error(self, message):
        return Response(
            json.dumps({
                "success": False,
                "message": message
            }),
            headers={'Content-Type': 'application/json'},
            status=400
        )
