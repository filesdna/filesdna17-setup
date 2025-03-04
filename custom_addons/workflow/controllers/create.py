import logging
import random
import string
from odoo import http
from odoo.http import request, Response
from odoo.addons.workflow.services.helpers import WorkflowHelper
import json

workflow_helper = WorkflowHelper()

_logger = logging.getLogger(__name__)

class WorkflowController(http.Controller):
    @http.route('/api/workflow/create-work-flow', type='http', auth='user', methods=['POST'], csrf=False)
    def create_workflow(self, **kwargs):
        """
        API to create a new workflow.

        :param name: Name of the workflow.
        :param type: Type of the workflow.
        :param folder: Folder ID for the workflow.
        :return: JSON response with the workflow details or an error message.
        """
        try:
            # Parse JSON payload if Content-Type is application/json
            if request.httprequest.content_type == 'application/json':
                kwargs = json.loads(request.httprequest.data.decode('utf-8'))

            _logger.info(f"Payload received: {kwargs}")

            # Validate user
            if not request.env.user:
                return Response(
                    json.dumps({"success": False, "message": "Invalid user"}),
                    content_type="application/json",
                    status=400
                )

            user_id = request.env.user.id

            # Extract inputs
            name = kwargs.get('name')
            workflow_type = kwargs.get('type')
            folder = kwargs.get('folder')
            _logger.info(f"workflow_type:{workflow_type}")
            if not name or not workflow_type:
                return Response(
                    json.dumps({"success": False, "message": "Missing required parameters"}),
                    content_type="application/json",
                    status=400
                )

            # Check for duplicate workflow name
            existing_count = request.env['workflow'].sudo().search_count([
                ('user_id', '=', user_id),
                ('name', '=', name),
                ('type', '=', workflow_type),
            ])

            if existing_count > 0:
                return Response(
                    json.dumps({"success": True, "message": "The name of workflow already exists."}),
                    content_type="application/json",
                    status=200
                )

            # Generate a unique hash key
            hash_key = ''.join(random.choices(string.ascii_letters + string.digits, k=20))

            # Create the workflow
            workflow = request.env['workflow'].sudo().create({
                'user_id': user_id,
                'hash_key': hash_key,
                'name': name,
                'type': workflow_type,
                'folder': folder,
            })

            # Add activity log
            data = {
                'type': 'created',
                'workflow_id': workflow.id,
                'message': "Workflow has been created",
            }
            workflow_helper.add_activity_log(data)

            # Prepare response
            response_data = {
                "success": True,
                "data": {
                    'id': workflow.id,
                    'name': workflow.name,
                    'type': workflow.type,
                    'folder': workflow.folder,
                    'hash_key': workflow.hash_key,
                },
            }

            return Response(
                json.dumps(response_data),
                content_type="application/json",
                status=200
            )

        except Exception as e:
            _logger.error(f"Error creating workflow: {str(e)}", exc_info=True)
            error_response = {
                "success": False,
                "message": f"An error occurred: {str(e)}",
            }
            return Response(
                json.dumps(error_response),
                content_type="application/json",
                status=500
            )
