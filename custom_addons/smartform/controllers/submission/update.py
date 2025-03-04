import logging
from odoo import http
from odoo.http import request
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class SubmissionUpdateController(http.Controller):

    @http.route('/submission/update', type='json', auth='public', methods=['POST'])
    def update_submission(self, **kwargs):
        try:
            # Extract input parameters
            ids = kwargs.get('ids')
            status = kwargs.get('status')

            # Ensure `ids` is a list and `status` is provided
            if not isinstance(ids, list) or not ids:
                raise UserError("Submission IDs must be provided as a non-empty list.")
            if status is None:
                raise UserError("Status is required.")

            if status not in ['0', '1', '2']:
                raise UserError("Invalid status value. Allowed values: 0, 1, 2.")

            # Convert the list of IDs to integers
            submission_ids = [int(id) for id in ids]

            # Search for the submissions to update
            submissions = request.env['submission'].sudo().search([('id', 'in', submission_ids)])
            if not submissions:
                return {'message': "No submissions found to update.", 'success': False}

            # Update the status of the submissions
            submissions.write({'status': status})

            # Determine the success message based on the status
            success_msg = (
                'Archived successfully' if status == '1' else
                'Moved to Trash successfully' if status == '2' else
                'Updated successfully'
            )

            return {
                'message': success_msg,
                'data': submissions.read(['id', 'status']),
                'success': True
            }

        except UserError as e:
            _logger.error(f"UserError: {str(e)}")
            return {'message': str(e), 'success': False}

        except Exception as e:
            _logger.error(f"Error updating submissions: {str(e)}")
            return {'message': "Error updating submission.", 'success': False}
