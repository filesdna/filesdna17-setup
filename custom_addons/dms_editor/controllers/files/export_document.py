from odoo import http
from odoo.http import request, Response
import json
import os
import logging
import time
import re
import base64
import string
import random
from datetime import datetime
from odoo.addons.dms_editor.services.pdf_editor import PdfEditorService
from odoo.addons.dms_editor.services.files import Files
from odoo.addons.dms_editor.services.blockchain import BlockchainService
from odoo.tools import config
from odoo.addons.dms_editor.services.google_storage import LocalStorageService


_logger = logging.getLogger(__name__)
pdf_service = PdfEditorService()
file_service = Files()
bc = BlockchainService()

server_path = config['server_path']

class FileFinishController(http.Controller):
    @http.route('/api/file/finish', type='http', auth='user', methods=['POST'], csrf=False)
    def finish_file(self, **kwargs):
        try:
            request_data = json.loads(request.httprequest.data.decode('utf-8'))
            document_id = request_data.get('document_id')
            timezone = request_data.get('timezone')
            action_type = request_data.get('type')
            json_data = request_data.get('json_data')

            hash = document_id.split('-')[0]
            current_time_seconds = document_id.split('-')[1]
            if not document_id:
                return self._response_error("Document ID is required.")

            user = request.env.user
            user_id = user.id
            created_at = int(time.time())

            check_file = request.env['dms.file'].sudo().search([
                ('sha512_hash', '=', hash),
                ('current_time_seconds', '=', current_time_seconds),
            ], limit=1)

            if not check_file:
                return self._response_error("Document not found.")

            temp_path = f'{server_path}/dms_editor/static/src'
            set_new_name = check_file.name
            file_name = check_file.attachment_id.store_fname.split('/')[1]
            full_name = f"{check_file.attachment_id.store_fname.split('-')[0]}-{created_at}"
            status = "Pending"

            # Handle JSON data and sign detection
            sign_change = False
            if json_data:
                sign_change = self._check_is_sign(json_data)
                if sign_change:
                    status = "Completed"

            if check_file.document_status == "pending_owner" and not sign_change:
                return self._response_error("Please put sign to finish document.")

            if action_type == "keep":
                set_new_name, file_name = self._pdf_export_name(check_file, user_id)

            # Modify PDF content
            try:
                get_edited_pdf = pdf_service.modify_pdf_content(json_data, check_file.id)
                if not get_edited_pdf:
                    raise Exception("Error modifying PDF content.")
                pat_f = os.path.join(temp_path, 'assets', 'pdf', get_edited_pdf)
            except Exception as e:
                _logger.error(f"Error modifying PDF content: {str(e)}")
                return self._response_error("Error modifying PDF.")

            # Handle export type
            if action_type == "export":
                try:
                    file_service.remove_all_images(check_file.id, remove_data=True)
                    tmp_path = f'{temp_path}/temp/{file_name}'
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except Exception as e:
                    _logger.error(f"Error removing images: {str(e)}")

            key_file = f"{server_path}/google_cloud_storage/google_creds.json"
            # Initialize Google Cloud Storage service
            gcs_service = LocalStorageService()
            db_name= request.env['ir.config_parameter'].sudo().get_param('web.base.url').split("//")[-1].split(".")[0]
            destination = f'{db_name}/{full_name}' if action_type == 'keep' else f'{db_name}/{check_file.attachment_id.store_fname}'

            if sign_change:
                sign_pdf = file_service.sign_pdf(get_edited_pdf, user, timezone)
                if not sign_pdf:
                    return self._response_error("Error code: 1102",status=500)
                pat_f = f'{temp_path}/assets/signpdf/{get_edited_pdf}'
                file_hash = file_service.file_hash(pat_f,'file')
                file_service.upload_to_gcs(pat_f, destination, encription=False)
            else:
                file_hash = file_service.file_hash(pat_f,'file')
                file_service.upload_to_gcs(pat_f, destination, encription=False)
            
            set_data = {
                "document_id": check_file.id,
                "user_id": user_id,
                "path": pat_f,
                "name": file_name,
            }
            blockchain_data = { 'user_id': user.blockchain_uid, 'hash': file_hash}

            # Create or update file record
            if action_type == "keep":
                with open(pat_f, 'rb') as pdf_file:
                    # Read the PDF file as binary
                    pdf_binary = pdf_file.read()
                    # Encode the binary data to base64
                    base64_encoded = base64.b64encode(pdf_binary).decode('utf-8')

                blockchain_result = bc.add_document_in_blockchain(blockchain_data)
                doc_record = request.env['dms.file'].sudo().create({
                    "name" : set_new_name,
                    "in_out": "in",
                    "confidentiality_level_id": 1,
                    "degree_of_secrecy":1,
                    'directory_id': check_file.directory_id.id,
                    'content' : base64_encoded,
                    'create_uid' : user_id,
                    'storage_id' : check_file.storage_id.id,
                    'current_time_seconds': created_at,
                    'company_id': user.company_id.id,
                    "document_status" : "Draft",
                    "bc_document": blockchain_result,
                })

                dms_version_count = request.env['document.version'].sudo().search_count([('document_id','=',check_file.id)])

                dms_version = request.env['document.version'].sudo().search([('document_id','=',doc_record.id),('name','=',set_new_name)], limit=1)
                dms_version.write({'document_id':check_file.id, 'version_number': dms_version_count + 1})
                check_file.write({
                    'current_version_id':dms_version.id
                })
                check_file.attachment_ids = [(6, 0, dms_version.attachment_ids.ids)]
                
                if not doc_record:  # Check if creation failed
                    return self._response_error("Failed to create new document.", status=500)

                set_data['document_id'] = doc_record.id
            else:
                blockchain_result = bc.add_document_in_blockchain(blockchain_data)
                dms_version_count = request.env['document.version'].sudo().search_count([('document_id','=',check_file.id)])
                dms_version = request.env['document.version'].sudo().search([('document_id','=',check_file.id),('name','=',set_new_name)], limit=1)

                dms_version.write({
                    'sha512_hash': file_hash,
                    'version_number': dms_version_count + 1
                })
                check_file.attachment_ids = [(6, 0, dms_version.attachment_ids.ids)]
                doc_record = check_file.write({
                    'name': set_new_name,
                    'bc_document': blockchain_result,
                    'sha512_hash': file_hash,
                    'current_version_id': dms_version.id
                })

                if not doc_record:  # Check if update failed
                    return self._response_error("Failed to update the document.", status=500)

                doc_record = request.env['dms.file'].sudo().browse(check_file.id)
            if sign_change:
                # Define the where condition
                where_con = [
                    ('document_id', '=', doc_record.id),
                    ('email', '=', user.email),
                    ('sent_by_email', '=', user.email)
                ]

                # Check if a record exists
                record_check = request.env['document.sign'].sudo().search(where_con, limit=1)

                if record_check:
                    # Update the existing record
                    record_check.sudo().write({'status': 'Signed'})
                else:
                    # Create a new record if not found
                    request.env['document.sign'].sudo().create({
                        'document_id': doc_record.id,
                        'email': user.email,
                        'user_hash': ''.join(random.choices(string.ascii_letters + string.digits, k=40)),
                        'sent_by_email': user.email,
                        'sent_by': user.name,
                        'status': 'Signed',
                        'order_by': 0,
                        'is_guest': 0,
                        'date': datetime.now().strftime("%Y-%m-%d"),
                        'is_last_completed': True,
                    })

                # Add the signature to the blockchain
                add_create_signature_bc = bc.add_signature_in_blockchain(doc_record.sha512_hash, user.blockchain_uid)

                if add_create_signature_bc:
                    # Add the document signature to the blockchain
                    file_service.document_sign_bc(
                        user.blockchain_uid,
                        doc_record.id,
                        doc_record.sha512_hash,
                        blockchain_result,
                        add_create_signature_bc['signature'],
                        user.email,
                        doc_record.create_uid
                    )

            # Append JSON data to the setData dictionary
            set_data['append_json'] = doc_record.append_json

            # Generate PDF pages
            file_service.generate_pdf_pages(set_data, None, status)
            return self._response_success("Export Finished")

        except Exception as e:
            _logger.error(f"Error finishing file: {str(e)}")
            return self._response_error("An error occurred.",status=500)

    def _response_error(self, message, status=400):
        return Response(
            json.dumps({"success": False, "message": message}),
            headers={'Content-Type': 'application/json'},
            status=status
        )

    def _response_success(self, message):
        return Response(
            json.dumps({"success": True, "message": message}),
            headers={'Content-Type': 'application/json'},
            status=200
        )

    def _check_is_sign(self, json_data):
        try:
            for item in json_data:
                if item.get('type') not in ['icon', 'qr', 'barcode', 'date', 'textbox1', 'setting', 'highlight', 'draw', 'date1', 'refnumber', 'image', 'watermark','mask']:
                    if not item.get('is_completed'):
                        return False
            return True
        except Exception as e:
            _logger.error(f"Error in _check_is_sign: {str(e)}")
            return False


    def _pdf_export_name(self, check_file, user_id):
        """
        Generate new names for exporting PDF files.

        :param check_file: Record containing file details (name, etc.)
        :param user_id: ID of the user
        :return: Tuple containing (set_new_name, file_name)
        """
        # Extract the base name before "_export_"
        doc_name = check_file.name.split('.pdf')[0]
        get_real_name = doc_name.split("_export_")[0]

        # Count existing exports with a similar name
        get_export_html_count = check_file.env['dms.file'].sudo().search_count([
            ('create_uid', '=', user_id),
            ('name', 'like', f"{get_real_name}_export_")
        ])

        # Initialize variables
        set_new_name = None
        replace = None
        file_name = None

        if get_export_html_count:
            # Handle second or subsequent exports
            if "_export_" in doc_name:
                # Extract export count
                get_export_count = doc_name.split("_")[-1]
                get_export_name = doc_name.replace(
                    f"_export_{get_export_count}", ""
                )

                # Increment export count
                export_count = int(get_export_count) if get_export_count.isdigit() else 1
                set_new_name = f"{get_export_name}_export_{export_count + 1}.pdf"
                replace = re.sub(r"[^A-Z0-9]+", "_", get_export_name)  # Replace non-alphanumeric chars with '_'
                file_name = f"{get_export_name}_export_{export_count + 1}-{int(time.time() * 1000)}.pdf"

            else:
                # Create name for first additional export
                set_new_name = f"{doc_name}_export_{get_export_html_count + 1}.pdf"
                replace = re.sub(r"[^A-Z0-9]+", "_", doc_name)
                file_name = f"{replace}_export_{get_export_html_count + 1}-{int(time.time() * 1000)}.pdf"

        else:
            # Handle first export
            set_new_name = f"{doc_name}_export_1.pdf"
            replace = re.sub(r"[^A-Z0-9]+", "_", doc_name)
            file_name = f"{replace}_export_1-{int(time.time() * 1000)}.pdf"

        return set_new_name, file_name