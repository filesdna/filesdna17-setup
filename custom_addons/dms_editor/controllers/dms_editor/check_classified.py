import logging
import json
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

class DocumentSecurityController(http.Controller):

    @http.route('/api/files/check-classified', type='http', auth='none', methods=['POST'], csrf=False)
    def check_classified(self, **kwargs):
        try:
            # Verify user and retrieve parameters
            user = request.env.user
            doc_id = kwargs.get('document_id')
            password = kwargs.get('password')
            user_id = user.id

            if not doc_id:
                response_data = {'success': False, 'message': "Document ID is required"}
                return Response(json.dumps(response_data), status=400, mimetype='application/json')

            # Extract hash and current time from the document ID
            parts = doc_id.split('-')
            if len(parts) < 2:
                response_data = {'success': False, 'message': "Invalid document ID format"}
                return Response(json.dumps(response_data), status=400, mimetype='application/json')

            hash = parts[0]
            current_time = int(parts[1])

            # Fetch the document based on `hash_url`
            document = request.env['dms.file'].sudo().search([
                ('sha512_hash', '=', hash), 
                ('current_time_seconds', '=', current_time)
            ], limit=1)
            
            if document:
                # Return if no special classification
                response_data = {'classified': False}
                return Response(json.dumps(response_data), status=200, mimetype='application/json')

            # Handle case where no document is found
            else:
                response_data = {'success': False, 'message': "No document found"}
                return Response(json.dumps(response_data), status=404, mimetype='application/json')

        except Exception as e:
            _logger.error(f"Error checking document classification: {str(e)}")
            response_data = {'success': False, 'message': "An error occurred while processing your request."}
            return Response(json.dumps(response_data), status=500, mimetype='application/json')
