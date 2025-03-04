import logging
import json
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

class SubmissionDeleteController(http.Controller):

    @http.route('/submission/delete', type='http', auth='public', methods=['POST'],csrf=False)
    def delete_submission(self, **kwargs):
        try:
            # Extract input parameters
            ids = kwargs.get('ids')
            if not ids:
                response_data = {
                    'message': 'Submission IDs are required.',
                    'success': False
                }
                return Response(json.dumps(response_data), status=400, mimetype='application/json')

            # Split the IDs and convert them to integers
            submission_ids = [int(id) for id in ids.split(',')]

            # Check if submissions exist
            submissions = request.env['submission'].sudo().search([('id', 'in', submission_ids)])
            if not submissions:
                response_data = {
                    'message': f'No submissions found with IDs {ids}.',
                    'success': False
                }
                return Response(json.dumps(response_data), status=404, mimetype='application/json')

            # Delete the submissions
            submissions.unlink()

            response_data = {
                'message': f'Submissions deleted',
                'success': True
            }
            return Response(json.dumps(response_data), status=200, mimetype='application/json')

        except Exception as e:
            _logger.error(f"Error deleting submissions: {str(e)}")
            response_data = {
                'message': f"Error: {str(e)}",
                'success': False
            }
            return Response(json.dumps(response_data), status=500, mimetype='application/json')
