from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class WorkflowUsersController(http.Controller):
    @http.route('/api/workflow/add-workflow-user', type='json', auth='user', methods=['POST'], csrf=False)
    def add_workflow_users(self, **kwargs):
        """
        API to add users to a workflow.

        :param hash_key: The hash key of the workflow.
        :param ids: A comma-separated string of user IDs to add.
        :return: JSON response indicating success or failure.
        """
        try:
            user = request.env.user
            user_id = user.id

            # Extract inputs
            hash_key = kwargs.get('hash_key')
            ids = kwargs.get('ids')

            if not hash_key or not ids:
                return {"success": False, "message": "Missing required parameters."}

            # Validate the workflow
            workflow = request.env['workflow'].sudo().search([('hash_key', '=', hash_key), ('user_id', '=', user_id)], limit=1)
            if not workflow:
                return {"success": False, "message": "Invalid hash key."}

            # Add users to the workflow
            user_ids = ids.split(",")
            for user_id in user_ids:
                existing_user = request.env['workflow.users'].sudo().search([('workflow_id', '=', workflow.id), ('user_id', '=', user_id)], limit=1)
                if not existing_user:
                    request.env['workflow.users'].sudo().create({'workflow_id': workflow.id, 'user_id': user_id})

            return {"success": True, "message": "Successfully added."}

        except Exception as e:
            _logger.error(f"Error in add_workflow_users: {str(e)}")
            return {"success": False, "message": f"An error occurred: {str(e)}"}
