from odoo import http
from odoo.http import request, Response
import json
import logging
import math
from odoo.tools import config 
from odoo.addons.dms_editor.services.google_storage import LocalStorageService
from datetime import datetime

_logger = logging.getLogger(__name__)
 
server_path = config['server_path']

class CommentsController(http.Controller):
    @http.route('/api/file/get-comments', type='http', auth='user', methods=['GET'], csrf=False)
    def get_comments(self, **kwargs):
        try:
            gcs = LocalStorageService()
            per_page = int(kwargs.get('per_page', request.env["ir.config_parameter"].sudo().get_param("per_page", default=10)))
            page = int(kwargs.get('page', 1))
            document_id = kwargs.get('document_id')
            hash = document_id.split('-')[0]
            current_time = int(document_id.split('-')[1])

            if not document_id:
                return self._response_error("Document ID is required.")
            
            # Retrieve document
            document = request.env['dms.file'].sudo().search([
                ('sha512_hash', '=', hash), 
                ('current_time_seconds', '=', current_time)
            ], limit=1)
            
            if not document:
                return self._response_error("Document not found.")

            where = [('document_id', '=', document.id)]

            total_records = request.env['document.comments'].sudo().search_count(where)
            total_pages = math.ceil(total_records / per_page)
            start_from = (page - 1) * per_page

            # Fetch comments
            comments = request.env['document.comments'].sudo().search(
                where, 
                limit=per_page, 
                offset=start_from, 
                order='create_date desc'
            )
            comment_ids = comments.mapped('id')

            # Fetch replies for comments
            replies = request.env['document.reply'].sudo().search([('comment_id', 'in', comment_ids)])
            c_user = request.env.user.id

            # Process replies
            processed_replies = []
            for reply in replies:
                _logger.info(f"Processing reply: ID {reply.id}, Comment ID {reply.comment_id}")
                reply_data = {
                    'id': reply.id,
                    'comment_id': reply.comment_id.id if reply.comment_id else None,
                    'message': reply.message,
                    'type': reply.reply_type,
                    'privacy': reply.privacy,
                    'user_id': reply.user_id.id if reply.user_id else None,
                    'name': reply.user_id.name if reply.user_id else '',
                    'email': reply.user_id.email if reply.user_id else '',
                    'createdat': int(reply.create_date.timestamp() * 1000) if reply.create_date else None,
                    'updatedat': int(reply.write_date.timestamp() * 1000) if reply.write_date else None,
                }
                processed_replies.append(reply_data)

            _logger.info(f"Processed Replies: {processed_replies}")

            comments_with_replies = []
            for comment in comments:
                _logger.info(f"Processing comment: ID {comment.id}")
                comment_data = {
                    'id': comment.id,
                    'document_id': comment.document_id.id,
                    'user_id': comment.user_id.id,
                    'name': comment.user_id.name if comment.user_id else '',
                    'email': comment.user_id.email if comment.user_id else '',
                    'message': comment.message,
                    'type': comment.comment_type,
                    'privacy': comment.privacy,
                    'position': json.loads(comment.position) if isinstance(comment.position, str) else comment.position,
                    'page_id': comment.page_id,
                    'createdat': int(comment.create_date.timestamp() * 1000) if comment.create_date else None,
                    'updatedat': int(comment.write_date.timestamp() * 1000) if comment.write_date else None,
                    'replies': [reply for reply in processed_replies if reply['comment_id'] == comment.id]
                }
                comments_with_replies.append(comment_data)

            _logger.info(f"Comments with Replies: {comments_with_replies}")

            # Prepare response
            response_data = {
                "total_count": total_records,
                "prev_enable": 1 if page > 1 else 0,
                "next_enable": 1 if page < total_pages else 0,
                "total_pages": total_pages,
                "per_page": per_page,
                "page": page,
                "data": comments_with_replies,
                "success": True
            }


            return Response(json.dumps(response_data), headers={'Content-Type': 'application/json'}, status=200)

        except Exception as e:
            _logger.error(f"Error fetching comments: {str(e)}")
            return self._response_error(f"An error occurred: {str(e)}")

    def _response_error(self, message):
        return Response(
            json.dumps({
                "success": False,
                "message": message
            }),
            headers={'Content-Type': 'application/json'},
            status=400
        )