from odoo import http
from odoo.http import request, Response
import json
import logging
import uuid
import os
from datetime import datetime, date
from odoo.addons.dms_editor.services.google_storage import LocalStorageService
from odoo.addons.dms_editor.services.email_template import create_log_note
from werkzeug.utils import secure_filename
from odoo.tools import config 
from odoo.addons.dms_editor.services.helpers import serialize_record

_logger = logging.getLogger(__name__)
 
server_path = config['server_path']

class AddCommentReplyController(http.Controller):
    @http.route('/api/file/add-sticky-comment', type='http', auth='user', methods=['POST'], csrf=False)
    def add_comment_reply(self, **kwargs):
        try:
            # Parse input parameters
            document_id = kwargs.get('document_id')
            message = kwargs.get('message', '')
            comment_type = kwargs.get('type', 'text')
            privacy = kwargs.get('privacy', 'public')
            position = kwargs.get('position')
            comment_id = kwargs.get('comment_id', '')
            page_id = kwargs.get('page_id')

            # Validate input parameters
            if not document_id or not position or not page_id:
                return self._response_error("Missing required parameters.")

            if comment_type not in ["text", "voice"] or privacy not in ["public", "private"]:
                return self._response_error("Invalid type or privacy value.")

            if comment_type == "voice" and not message:
                return self._response_error("Voice file is required for voice comments.")

            # Fetch the document
            file_data = request.env['dms.file'].sudo().search([('id', '=', document_id)], limit=1)

            if not file_data:
                return self._response_error("Document not found.")

            # Get the current user
            current_user = request.env.user

            # Prepare data for comment or reply
            if comment_id:
                # It's a reply, so use `comment_id`
                comment_data = {
                    'comment_id': comment_id,
                    'user_id': current_user.id,
                    'reply_type': comment_type,  # For replies, use `reply_type`
                    'privacy': privacy,
                    'message': message,  # Pass the message
                }
            else:
                # It's a comment, so use `document_id`
                comment_data = {
                    'document_id': file_data.id,
                    'user_id': current_user.id,
                    'comment_type': comment_type,  # For comments, use `comment_type`
                    'privacy': privacy,
                    'message': message,  # Pass the message
                    'page_id': page_id,
                    'position': position,
                }
            # Handle voice message upload
            if comment_type == "voice":
                unique_filename = f"{uuid.uuid4().hex}.mp3"
                temp_file_path = os.path.join(f'{server_path}/dms_editor/static/src/temp', secure_filename(unique_filename))
                upload_file = message
                with open(temp_file_path, 'wb') as f:
                    f.write(upload_file.read())
                gcs = LocalStorageService()
                db_name= request._cr.dbname
                destination_path = f"{db_name}/voice/{unique_filename}"

                upload_result = gcs.upload_file(temp_file_path, destination_path, None)

                if not upload_result:
                    return self._response_error("Problem while recording voice.")

                comment_data['message'] = gcs.read_url(destination_path)
            else:
                # Validate text message
                if not message:
                    return self._response_error("Comment cannot be blank.")

                comment_data['message'] = message

            # Create the comment or reply
            model = 'document.comments' if not comment_id else 'document.reply'
            record = request.env[model].sudo().create(comment_data)

            create_log_note(document_id,f"{current_user.name}  {'added a comment' if not comment_id else 'replied to a comment'}")
            
            # Return success response
            return self._response_success(f"{'Reply' if comment_id else 'Comment'} has been added.", record)

        except Exception as e:
            _logger.error(f"Error adding comment or reply: {str(e)}")
            return self._response_error(f"An error occurred: {str(e)}")

    def _response_error(self, message, status=400):
        """
        Generate error response.
        """
        return Response(
            json.dumps({"success": False, "message": message}),
            headers={'Content-Type': 'application/json'},
            status=status
        )

    def _response_success(self, message, record):
        """
        Generate success response with serialized data and transform keys.
        """
        if record:
            record_data = record.read()[0]
            # Rename `comment_type` and `reply_type` to `type`
            if 'comment_type' in record_data:
                record_data['type'] = record_data.pop('comment_type')
            if 'reply_type' in record_data:
                record_data['type'] = record_data.pop('reply_type')
            # Convert `create_date` and `write_date` to timestamps (in milliseconds)
            if 'create_date' in record_data and isinstance(record_data['create_date'], (datetime, date)):
                record_data['create_date'] = int(record_data['create_date'].timestamp() * 1000)
            if 'write_date' in record_data and isinstance(record_data['write_date'], (datetime, date)):
                record_data['write_date'] = int(record_data['write_date'].timestamp() * 1000)
            # Serialize the record
            serialized_data = serialize_record(record_data)
        else:
            serialized_data = {}

        return Response(
            json.dumps({"success": True, "message": message, "data": serialized_data}),
            headers={'Content-Type': 'application/json'},
            status=200
        )