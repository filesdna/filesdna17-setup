from odoo import http
from odoo.http import request, Response
import logging
import json
import os
from datetime import datetime, date

_logger = logging.getLogger(__name__)

def custom_serializer(obj):
    """
    Custom JSON serializer for objects not serializable by default json code
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()  # Convert to ISO format (e.g., 'YYYY-MM-DDTHH:MM:SS')
    elif isinstance(obj, bytes):
        return obj.decode('utf-8')  # Decode bytes to string
    raise TypeError(f"Type {type(obj)} not serializable")

class WorkflowAssignFormsController(http.Controller):
    @http.route('/api/workflow/get-assign-forms', type='http', auth='user', methods=['GET'], csrf=False)
    def assign_forms(self, **kwargs):
        """
        API to fetch forms assigned to the current user's email.

        :return: JSON response with the list of assigned forms and related workflows.
        """
        try:
            # Get the current user
            user_email = request.env.user.login

            # Fetch forms assigned to the user's email
            assigned_forms = request.env['workflow.forms'].sudo().search([('assign_email', '=', user_email)])
            form_data = []

            for form in assigned_forms:
                # Validate workflow_id and form_id
                if not form.workflow_id or not form.form_id:
                    _logger.warning(f"Invalid form or workflow ID for form record: {form.id}")
                    continue

                _logger.info(f"Processing form_id: {form.form_id}, workflow_id: {form.workflow_id.id}")

                # Fetch related workflow and form details
                workflow = request.env['workflow'].sudo().search([('id', '=', form.workflow_id.id)], limit=1)
                wform = request.env['smart.form'].sudo().search([('id', '=', form.form_id)], limit=1)

                # Skip invalid workflow or form records
                if not workflow or not wform:
                    _logger.warning(f"Skipping form with invalid workflow or form: {form.id}")
                    continue

                form_data.append({
                    'form': wform.read()[0] if wform else None,
                    'workflow': workflow.read()[0] if workflow else None,
                    'assign_email': form.assign_email,
                    'status': form.status,
                    'node_id': form.node_id,
                })

            # Return success response
            response_data = {
                "success": True,
                "data": form_data,
            }
            return Response(
                json.dumps(response_data,default=custom_serializer),
                content_type="application/json",
                status=200,
            )

        except Exception as e:
            _logger.error(f"Error in assign_forms: {str(e)}")
            # Return error response
            response_data = {
                "success": False,
                "message": f"An error occurred: {str(e)}",
            }
            return Response(
                json.dumps(response_data),
                content_type="application/json",
                status=500,
            )