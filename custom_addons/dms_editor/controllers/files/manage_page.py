from odoo import http
from odoo.http import request, Response
import json
import os
import logging
import base64
from datetime import datetime
import fitz  # PyMuPDF
from odoo.addons.dms_editor.services.files import Files
from odoo.addons.dms_editor.services.blockchain import BlockchainService
from odoo.addons.dms_editor.services.google_storage import LocalStorageService
from odoo.tools import config

_logger = logging.getLogger(__name__)

server_path = config['server_path']

class ManagePageController(http.Controller):
    @http.route('/api/file/manage-page', type='http', auth='user', methods=['POST'], csrf=False)
    def manage_page(self, **kwargs):
        try:
            # Parse request data
            request_data = json.loads(request.httprequest.data.decode('utf-8'))
            document_id = request_data.get('document_id')
            index = request_data.get('index') - 1  # Adjust index (0-based)
            method = request_data.get('method')

            # Validate inputs
            if not document_id or method not in ['add', 'remove', 'copy']:
                return self._response_error("Invalid Parameters")

            # Split document ID to retrieve hash and timestamp
            hash = document_id.split('-')[0]
            current_time = document_id.split('-')[1]

            # Fetch the document
            get_file = request.env['dms.file'].sudo().search([
                ('sha512_hash', '=', hash),
                ('current_time_seconds', '=', current_time)
            ], limit=1)

            if not get_file:
                return self._response_error("Document not found")

            # Initialize Google Cloud Storage
            key_file = f"{server_path}/google_cloud_storage/google_creds.json"
            gcs_service = LocalStorageService()
            temp_path = f'{server_path}/dms_editor/static/src/temp'
            local_file_path = os.path.join(temp_path, get_file.attachment_id.store_fname.split('/')[1])
            db_name= request.env['ir.config_parameter'].sudo().get_param('web.base.url').split("//")[-1].split(".")[0]
            # Download PDF from Google Cloud
            gcs_service.download_file(f'{db_name}/{get_file.attachment_id.store_fname}', local_file_path, encryption_key=None)

            # Open the PDF using PyMuPDF (fitz)
            pdf_document = fitz.open(local_file_path)

            if method == 'add':
                # Add a blank page
                pdf_document.insert_page(index + 1, width=595, height=842)  # A4 size
            elif method == 'copy':
                # Copy an existing page and insert it
                temp_pdf = fitz.open()
                temp_pdf.insert_pdf(pdf_document, from_page=index, to_page=index)  # Copy to temp PDF

                # Insert the copied page into the original PDF
                pdf_document.insert_pdf(temp_pdf, start_at=index)
            elif method == 'remove':
                # Remove the specified page
                pdf_document.delete_page(index + 1)
            
            # Save changes to a temporary file first
            temp_updated_file = os.path.join(temp_path, f"{get_file.attachment_id.store_fname.split('/')[1]}_temp")
            pdf_document.save(temp_updated_file)  # Save changes to a temp file
            pdf_document.close()
            _logger.info(f"Changes saved to {temp_updated_file}.")

            # Replace the original file with the updated file
            os.replace(temp_updated_file, local_file_path)  # Overwrite the original file
            _logger.info(f"Original file replaced with updated file: {local_file_path}.")
            
            # Generate file hash
            file_service = Files()
            file_hash = file_service.file_hash(local_file_path, 'file')

            # Upload updated PDF to Google Cloud
            gcs_service.upload_file(local_file_path, f'{db_name}/{get_file.attachment_id.store_fname}', encryption_key=None)

            # Add to blockchain
            bc_service = BlockchainService()
            blockchain_data = {
                'user_id': request.env.user.blockchain_uid,
                'hash': file_hash,
            }
            blockchain_result = bc_service.add_document_in_blockchain(blockchain_data)

            # Update document details in the database
            get_file.sudo().write({
                'bc_document': blockchain_result,
                'sha512_hash': file_hash,
            })
            version = request.env['document.version'].sudo().search([('document_id','=',get_file.id),('name','=',get_file.name)], limit=1)
            version.write({'sha512_hash': file_hash})
            # Return success response
            return self._response_success("Success to manage page.", f'{file_hash}-{get_file.current_time_seconds}')

        except Exception as e:
            _logger.error(f"Error in manage_page: {str(e)}")
            return self._response_error("An error occurred while managing the document.")

    # Response error helper
    def _response_error(self, message, status=400):
        return Response(
            json.dumps({"success": False, "message": message}),
            headers={'Content-Type': 'application/json'},
            status=status
        )

    # Response success helper
    def _response_success(self, message, data):
        return Response(
            json.dumps({"success": True, "message": message, "data": data}),
            headers={'Content-Type': 'application/json'},
            status=200
        )
