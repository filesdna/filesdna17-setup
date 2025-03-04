import logging
import json
from odoo import http
from odoo.http import request
from odoo.exceptions import UserError
from datetime import datetime

_logger = logging.getLogger(__name__)

class SubmissionController(http.Controller):

    @http.route('/submission/index', type='http', auth='public', methods=['GET'])
    def index_submission(self, **kwargs):
        try:
            # Extract query parameters from the GET request
            form_id = kwargs.get('form_id')
            status = kwargs.get('status', '0')  # Default to 0

            if not form_id:
                raise UserError("Form ID is required.")

            if status not in ['0', '1', '2']:
                raise UserError("Invalid status value. Allowed values: 0, 1, 2.")

            # Fetch submissions with the given form_id and status
            submissions = request.env['submission'].sudo().search([
                ('form_id', '=', form_id),
                # ('status', '=', status)
            ])

            # Fetch the form to retrieve the user_id
            form = request.env['smart.form'].sudo().search([('hash', '=', form_id)], limit=1)
            if not form:
                return http.Response(
                    json.dumps({'message': f"Form with ID {form_id} not found.", 'success': False}),
                    status=404,
                    mimetype='application/json'
                )

            # Build the response data with the submission information
            def convert_datetime_fields(submission):
                response_submission = {
                        'id': submission['id'],
                        'form_id': submission['form_id'],
                        'status': int(submission['status']),
                        'from_user': "" if not submission.get('from_user') else submission['from_user'],
                        'createdat': submission['create_date'].isoformat() if isinstance(submission['create_date'], datetime) else submission['create_date'],
                        'updatedat': submission['write_date'].isoformat() if isinstance(submission['write_date'], datetime) else submission['write_date'],
                        'data': submission['data'],  # Include other fields as necessary
                    }
                return response_submission

            # Process submissions and convert datetime fields
            response_data = {
                'message': "Form submissions read!",
                'data': [
                    convert_datetime_fields(submission)
                    for submission in submissions.read(['id', 'form_id', 'status', 'data', 'from_user', 'create_date', 'write_date'])
                ],
                'user_id': form.user_id.id,
                'success': True
            }


            return http.Response(
                json.dumps(response_data),
                status=200,
                mimetype='application/json'
                )


        except UserError as e:
            _logger.error(f"UserError: {str(e)}")
            return http.Response(
                json.dumps({'message': str(e), 'success': False}),
                status=400,
                mimetype='application/json'
            )

        except Exception as e:
            _logger.error(f"Error reading submissions: {str(e)}")
            return http.Response(
                json.dumps({'message': "Error reading submissions.", 'success': False}),
                status=500,
                mimetype='application/json'
            )
