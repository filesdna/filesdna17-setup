import os
import logging
import json
from odoo import http
from odoo.http import request, Response
from odoo.tools import config
from odoo.addons.dms_editor.services.google_storage import LocalStorageService

_logger = logging.getLogger(__name__)
 
server_path = config['server_path']


class DocumentAppendDataController(http.Controller):

    @http.route(['/api/files/get-append-data/<string:id>/<string:json_version>','/api/files/get-append-data/<string:id>'], type='http', auth='public', methods=['GET'], csrf=False)
    def get_append_data(self, id, json_version=None, **kwargs):
        try:
            hash_url = id
            document = None
            
            # Fetch document based on `hash_url`
            if '-' in hash_url and len(hash_url.split('-')) > 1:
                hash = hash_url.split('-')[0]
                current_time = int(hash_url.split('-')[1])
                document = request.env['dms.file'].sudo().search([ ('sha512_hash', '=', hash), ('current_time_seconds', '=', current_time)], limit=1)

            if not document and hash_url.isdigit():
                # If hash_url is numeric, search by ID
                document = request.env['dms.file'].sudo().search([
                    ('id', '=', int(hash_url))
                ], limit=1)

            if not document:
                # Try finding a document from DocumentSign if previous searches failed
                sign = request.env['document.sign'].sudo().search([
                    ('user_hash', '=', hash_url)
                ], limit=1)
                if sign:
                    document = request.env['dms.file'].sudo().search([
                        ('id', '=', sign.document_id.id)
                    ], limit=1)

            # Check if the document was found
            if not document:
                return Response(
                    json.dumps({'success': False, 'message': "Document not found"}),
                    status=404,
                    mimetype='application/json'
                )

            # If status is `Completed` or `Pending Owner`, clear `append_json` data
            if document.document_status in ['Completed', 'pending_owner']:
                document.write({'append_json': None})
                return Response(
                    json.dumps({
                        'success': False,
                        'message': "No append data...",
                        'append_json': None
                    }),
                    status=200,
                    mimetype='application/json'
                )

            # Fetch `append_json` data
            append_json = document.append_json
            if json_version:
                append_version = request.env['dms.json.version'].sudo().search([
                    ('document_id', '=', document.id),
                    ('version', '=', json_version)
                ], limit=1)
                if append_version:
                    append_json = append_version.append_json

            if not append_json:
                return Response(
                    json.dumps({
                        'success': False,
                        'message': "No append data...",
                        'append_json': None
                    }),
                    status=200,
                    mimetype='application/json'
                )

            # Define paths and download append JSON if not locally available
            temp_dir = f"{server_path}/dms_editor/static/src/temp"
            local_append_path = os.path.join(temp_dir, append_json)
            db_name= request._cr.dbname
            destination_path = f"{db_name}/append_jsons/{append_json}"
            _logger.info(f"destination_path:{destination_path}")
            if not os.path.exists(local_append_path):
                # Retrieve encryption key for download
                key = request.env.user.company_id.encription_key
                _logger.info(f"key:{key}")
                gcs_service = LocalStorageService()
                gcs_service.download_file(destination_path, local_append_path, encryption_key=key)

            # Serve the append JSON file
            return http.send_file(local_append_path)

        except Exception as e:
            _logger.error(f"Error retrieving append data: {str(e)}")
            return Response(
                json.dumps({'success': False, 'message': "An error occurred while processing your request."}),
                status=500,
                mimetype='application/json'
            )
