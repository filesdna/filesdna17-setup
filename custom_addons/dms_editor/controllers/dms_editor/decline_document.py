from odoo import http
from odoo.http import request, Response
import json
import uuid
import logging
import os
import requests
from odoo.tools import config 
from werkzeug.utils import secure_filename
from datetime import datetime
from odoo.addons.dms_editor.services.email_template import mail_data, notify
from odoo.addons.dms_editor.services.google_storage import LocalStorageService

_logger = logging.getLogger(__name__)
 
server_path = config['server_path']

class DeclineDocumentController(http.Controller):
    @http.route('/api/file/decline', type='http', auth='public', methods=['POST'], csrf=False)
    def decline_document(self, **kwargs):
        """
        Decline a document based on the provided hash and reason.

        :param kwargs: JSON payload with 'hash', 'reason', and 'message_type'.
        :return: JSON response indicating success or failure.
        """
        try:
            hash_value = kwargs.get('hash')
            reason = kwargs.get('reason')
            message_type = kwargs.get('message_type', '')
            _logger.info(f"Hash value: {hash_value}")
            _logger.info(f"Reason: {reason}")
            _logger.info(f"Message type: {message_type}")
            if not hash_value:
                return self._response_error("Hash is required.")

            # Find the pending document to decline
            document_sign = request.env['document.sign'].sudo().search([
                ('user_hash', '=', hash_value),
                ('status', '=', 'Pending')
            ], limit=1)

            if not document_sign:
                return self._response_error("Hash not found.")

            # Validate file input
            if not reason:
                return self._response_error("reason is required.")

            # Handle voice message upload
            _logger.info(f"request.httprequest.files:{reason}")
            if message_type == "voice" and reason:
                upload_file = reason
                if upload_file:
                    reason = self.upload_voice_service(upload_file)

            _logger.info(f"reason:{reason}")

            # Update document status to 'Declined'
            document_sign.write({
                'status': 'Declined',
                'reason': reason or None
            })

            # Check if all documents are processed
            total_count = request.env['document.sign'].sudo().search_count([
                ('document_id', '=', document_sign.document_id.id)
            ])
            declined_count = request.env['document.sign'].sudo().search_count([
                ('document_id', '=', document_sign.document_id.id),
                ('status', 'in', ['Signed', 'Declined'])
            ])
            if total_count == declined_count:
                request.env['dms.file'].sudo().browse(document_sign.document_id.id).write({
                    'document_status': 'Declined'
                })

                doc_sign = request.env['document.sign'].sudo().search([
                    ('document_id', '=', document_sign.document_id.id)
                ])
                for doc in doc_sign:
                    registered_user = request.env["res.users"].sudo().search([("email", "=", doc.email)], limit=1)
                    mail_data(
                        email_type="public", 
                        subject=f"Declined Document - {document_sign.document_id.name}",  
                        email_to=doc.email,
                        header="Document declined", 
                        description=f"{request.env.user.name} declined {document_sign.document_id.name} document",
                    )
                    if registered_user:
                        notify(registered_user.id,f"{request.env.user.name} declined {document_sign.document_id.name} document", 'dms.file', document_sign.document_id.id)    
            # Return success response
            return self._response_success("You have declined the document successfully.")

        except Exception as e:
            _logger.error(f"Error in declining document: {str(e)}")
            return self._response_error(f"An error occurred: {str(e)}")


    def upload_voice_service(self,upload_file):
        """
        Upload a voice file to Google Cloud Storage.

        :param upload_file: Werkzeug FileStorage object from request.httprequest.files
        :return: URL of the uploaded voice file or False if the upload fails
        """
        temp_file_path = None

        try:
            # Initialize Google Cloud Storage service
            gcs = LocalStorageService()
            # Generate a unique filename for the uploaded file
            unique_filename = f"{uuid.uuid4().hex[:7]}{int(datetime.now().timestamp())}.mp3"
            temp_file_path = os.path.join(f'{server_path}/dms_editor/static/src/temp', secure_filename(unique_filename))

            # Save the uploaded file to a temporary location
            if not hasattr(upload_file, 'save'):
                _logger.error("Provided upload_file is not a valid FileStorage object.")
                return False

            try:
                with open(temp_file_path, 'wb') as f:
                    f.write(upload_file.read())
                _logger.info(f"Temporary file saved at: {temp_file_path}")
            except Exception as e:
                _logger.error(f"Error saving file to {temp_file_path}: {str(e)}")
                return False

            # Upload the file to Google Cloud Storage
            db_name= request.env['ir.config_parameter'].sudo().get_param('web.base.url').split("//")[-1].split(".")[0]
            destination_path = f"{db_name}/voice/{unique_filename}"
            upload_result = gcs.upload_file(temp_file_path, destination_path,None)

            if upload_result:
                file_url = gcs.read_url(destination_path)
                _logger.info(f"File uploaded to: {file_url}")
                return file_url

            _logger.error("Failed to upload the voice file to the bucket.")
            return False

        except Exception as e:
            _logger.error(f"Error uploading voice file: {str(e)}")
            return False

        finally:
            # Clean up the temporary file if it exists
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                _logger.info(f"Temporary file deleted: {temp_file_path}")

    def _response_success(self, message):
        """
        Generate success response.
        """
        return Response(
            json.dumps({
                "success": True,
                "message": message
            }),
            headers={'Content-Type': 'application/json'},
            status=200
        )

    def _response_error(self, message):
        """
        Generate error response.
        """
        return Response(
            json.dumps({
                "success": False,
                "message": message
            }),
            headers={'Content-Type': 'application/json'},
            status=400
        )
