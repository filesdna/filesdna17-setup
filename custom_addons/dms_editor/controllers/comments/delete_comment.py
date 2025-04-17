from odoo import http
from odoo.http import request, Response
import json
import logging
from odoo.addons.dms_editor.services.google_storage import LocalStorageService
from odoo.addons.dms_editor.services.email_template import create_log_note
from odoo.tools import config

_logger = logging.getLogger(__name__)
 
server_path = config['server_path']

def delete_voice(data):
    """
    Delete voice files from Google Cloud Storage.

    :param data: List of records with 'type' and 'message' fields.
    """
    gcs = LocalStorageService()
    for element in data:
        if element.get('type') == "voice":
            db_name= request._cr.dbname
            file_path = f"{db_name}/voice/{element.get('message').split('/')[-1]}"
            gcs.delete_file(file_path)

class DeleteCommentController(http.Controller):
    @http.route('/api/file/delete-comment', type='http', auth='user', methods=['POST'], csrf=False)
    def delete_comment(self, **kwargs):
        try:
            request_data = json.loads(request.httprequest.data.decode('utf-8'))
            # Parse input parameters
            comment_id = request_data.get('comment_id')
            comment_type = request_data.get('type', 'comment')

            if not comment_id:
                return self._response_error("Comment ID is required.")

            # Get the current user
            current_user = request.env.user

            # Fetch the comment or reply
            if comment_type == "comment":
                comment = request.env['document.comments'].sudo().search([('id', '=', comment_id), ('user_id', '=', current_user.id)], limit=1)
                if not comment:
                    return self._response_error("Comment not found or unauthorized.")

                # Delete associated replies
                replies = request.env['document.reply'].sudo().search([('comment_id', '=', comment.id)])
                delete_voice([{
                    'type': reply.reply_type,
                    'message': reply.message
                } for reply in replies])
                replies.unlink()


                # Delete the comment
                delete_voice([{
                    'type': comment.comment_type,
                    'message': comment.message
                }])
                comment.unlink()
                
                # Log activity
                create_log_note(comment.document_id.id,f"{current_user.name} deleted a comment")

            else:  # Deleting a reply
                reply = request.env['document.reply'].sudo().search([('id', '=', comment_id), ('user_id', '=', current_user.id)], limit=1)
                if not reply:
                    return self._response_error("Reply not found or unauthorized.")
        
                delete_voice([{
                    'type': reply.reply_type,
                    'message': reply.message
                }])
                reply.unlink()


            # Return success response
            return self._response_success("Comment or reply has been deleted.")

        except Exception as e:
            _logger.error(f"Error deleting comment or reply: {str(e)}")
            return self._response_error(f"An error occurred: {str(e)}")

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
