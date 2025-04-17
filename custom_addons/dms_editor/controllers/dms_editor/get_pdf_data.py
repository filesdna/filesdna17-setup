import logging
import os
import json
from odoo import http
from odoo.http import request, Response
from odoo.tools import config
from odoo.addons.dms_editor.services.google_storage import LocalStorageService

_logger = logging.getLogger(__name__)
 
server_path = config['server_path']

class DocumentPDFDataController(http.Controller):

    @http.route('/api/files/get-pdf-data/<string:id>', type='http', auth='none', methods=['GET'], csrf=False)
    def get_pdf_data(self, id, **kwargs):
        try:
            # Extract hash and current time from the URL parameter
            if not id:
                response_data = {'success': False, 'message': "Invalid Parameters"}
                return Response(json.dumps(response_data), status=400, mimetype='application/json')

            document = None
            if '-' in id and len(id.split('-')) > 1:
                hash = id.split('-')[0]
                current_time = int(id.split('-')[1])
                document = request.env['dms.file'].sudo().search([ ('sha512_hash', '=', hash), ('current_time_seconds', '=', current_time)], limit=1)
            else:
                hash = id

            # Search for the document in the database            
            if not document:
                sign = request.env['document.sign'].sudo().search([('user_hash', '=', hash)], limit=1)
                if sign:
                    document = request.env['dms.file'].sudo().search([ ('id', '=', sign.document_id.id)], limit=1)
            
            if document:
                # Set paths for the temporary storage and Google Cloud
                temp_path = f"{server_path}/dms_editor/static/src/temp"
                local_pdf_path = os.path.join(temp_path, os.path.basename(document.attachment_id.store_fname))
                key_file = f"{server_path}/google_cloud_storage/google_creds.json"
                db_name= request._cr.dbname
                destination_path = f"{db_name}/{document.attachment_id.store_fname}"

                # Ensure the temporary directory exists
                os.makedirs(temp_path, exist_ok=True)

                # Always attempt to download from Google Cloud Storage
                gcs_service = LocalStorageService()

                # Remove local file if it already exists
                if os.path.exists(local_pdf_path):
                    os.remove(local_pdf_path)

                # Download the latest version from Google Cloud Storage
                gcs_service.download_file(destination_path, local_pdf_path, encryption_key=None)

                # Serve the file
                return http.send_file(local_pdf_path)
            else:
                response_data = {'success': False, 'message': "Document not found"}
                return Response(json.dumps(response_data), status=404, mimetype='application/json')

        except Exception as e:
            _logger.error(f"Error retrieving PDF data: {str(e)}")
            response_data = {'success': False, 'message': "An error occurred while processing your request."}
            return Response(json.dumps(response_data), status=500, mimetype='application/json')
