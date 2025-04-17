import logging
import json
import base64
import os
from odoo import http, fields
from odoo.http import request, Response
from datetime import datetime
from odoo.tools import config
from odoo.addons.dms_editor.services.google_storage import LocalStorageService
from odoo.addons.dms_editor.services.signers import DocumentSignService

_logger = logging.getLogger(__name__)
 
server_path = config['server_path']

class AppendDataController(http.Controller):

    @http.route('/api/file/append', type='http', auth='public', methods=['POST'], csrf=False)
    def save_document(self, **kwargs):
        try:
            # Extract inputs and parse JSON fields
            document_id = kwargs.get("document_id")
            json_data = json.loads(kwargs.get("json_data", "[]"))  # Parse JSON string into a list
            location = kwargs.get("location", "")
            doc_type = kwargs.get("type", "")
            
            # Parse json_version field
            json_version_str = kwargs.get("json_version", "{}")
            json_version = json.loads(json_version_str) if json_version_str else {}
            
            # Parse user data
            user_data = json.loads(kwargs.get("user", "{}"))  # Parse JSON string into a dictionary


            # Retrieve document based on different id types
            document = self._retrieve_document(document_id)
            if not document:
                return Response(
                    json.dumps({"message": "Document not found.", "success": False}),
                    status=404,
                    mimetype='application/json'
                )
            if document.append_json:
                self.get_append_data(document.append_json, document.encription_user_id.company_id.encription_key)

            json_filename = f"{document.name.split('.')[0]}-{int(datetime.now().timestamp())}.json"
            local_file_path = f"{server_path}/dms_editor/static/src/temp"
            json_filepath = os.path.join(local_file_path, json_filename)
            with open(json_filepath, "w", encoding="utf-8") as file:
                json.dump(json_data, file)
            
            # Upload JSON to Google Cloud Storage
            upload_success = self._upload_to_gcs(json_filepath, json_filename, document.encription_user_id.company_id.encription_key)
            if not upload_success:
                return Response(
                    json.dumps({"message": "Error saving document.", "success": False}),
                    status=500,
                    mimetype='application/json'
                )

            # Update the document record with new JSON information
            self._update_document_record(document, json_filename, json_version, doc_type, json_data)

            # Return success response
            return Response(
                json.dumps({"message": "Document has been saved.", "success": True}),
                status=200,
                mimetype='application/json'
            )

        except Exception as e:
            _logger.error(f"Error saving document: {str(e)}")
            return Response(
                json.dumps({"message": "An error occurred while saving the document.", "success": False}),
                status=500,
                mimetype='application/json'
            )

    def _retrieve_document(self, document_id):
        """Retrieve document by ID or hash."""
        if document_id.isdigit():
            document = request.env['dms.file'].sudo().search([('id', '=', int(document_id))], limit=1)
        else:
            document_sign = request.env['document.sign'].sudo().search([('user_hash', '=', document_id)], limit=1)
            if document_sign:
                document = request.env['dms.file'].sudo().search([('id', '=', document_sign.document_id.id)], limit=1)
            else:
                document = request.env['dms.file'].sudo().search([('sha512_hash', '=', document_id.split('-')[0]),('current_time_seconds', '=', document_id.split('-')[1])], limit=1)
        return document


    
    def _upload_to_gcs(self, file_path, filename, encryption_key):
        """Upload file to Google Cloud Storage."""
        try:
            db_name= request._cr.dbname
            # Prepare upload details
            key_file = f"{server_path}/google_cloud_storage/google_creds.json"
            destination = f"{db_name}/append_jsons/{filename}"

            # Initialize Google Cloud Storage service
            gcs_service = LocalStorageService()
            gcs_service.upload_file(file_path, destination, encryption_key)
            return True
        except Exception as e:
            _logger.error(f"Failed to upload JSON file to GCS: {str(e)}")
            return False


    def _update_document_record(self, document, json_file, json_version, doc_type, json_data):
        """Update the document record with the new JSON data and version."""
        version = json_version.get("version", 0) if not isinstance(json_version, int) else json_version

        update_values = {'append_json': json_file}
        if document.document_status == 'Draft':
            update_values['document_status'] = 'Pending'

        # Check if custom reference number exists and update accordingly
        custom_ref = next((item for item in json_data if item.get('type') == 'refnumber' and item.get('selectedRef') == 'custom'), None)
        if custom_ref and document.doc_type != "Template":
            update_values['ref_number'] = custom_ref.get('data')
        
        # Handle JSON versioning
        existing_versions = request.env['dms.json.version'].sudo().search_count([('document_id', '=', document.id)])
        if doc_type != "update":
            if json_version.get("file_action") == 'send':
                request.env['dms.json.version'].sudo().search([
                    ('document_id', '=', document.id),
                    ('version', '=', version),
                ]).write({'append_json': json_file})
                update_values['json_version'] = version
            else:
                if version == existing_versions and existing_versions < 5:
                    request.env['dms.json.version'].sudo().create({
                        'document_id': document.id,
                        'append_json': json_file,
                        'version': existing_versions + 1,
                    })
                    update_values['json_version'] = existing_versions + 1
                elif existing_versions >= version:
                    request.env['dms.json.version'].sudo().search([
                        ('document_id', '=', document.id),
                        ('version', '>=', version),
                    ]).unlink()
                    request.env['dms.json.version'].sudo().create({
                        'document_id': document.id,
                        'append_json': json_file,
                        'version': version,
                    })
                    update_values['json_version'] = version

        # Apply the update to the document
        document.write(update_values)
        file = DocumentSignService()
        user_id = document.create_uid.id
        user = request.env['res.users'].sudo().search([('id', '=', user_id)], limit=1)
        if doc_type == 'save' and user:
            file.save_json_data(json_data, user, document)

    def get_append_data(self, route, key):
        """Retrieve append data."""
        try:
            # Define path for JSON retrieval based on the environment setup
            _temp = f"{server_path}/dms_editor/static/src/temp"
            json_filepath = os.path.join(_temp, route)
            if os.path.exists(json_filepath):
                os.remove(json_filepath)
            db_name= request._cr.dbname
            key_file = f"{server_path}/google_cloud_storage/google_creds.json"
            destination_path = f"{db_name}/append_jsons/{route}"
            gcs_service = LocalStorageService()
            gcs_service.download_file(destination_path, json_filepath, encryption_key=key)
            with open(json_filepath, 'r', encoding='utf-8') as file:
                content = file.read()
                return json.loads(content)
        except Exception as e:
            _logger.error(f"Error retrieving append data: {str(e)}")
            return []
