import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class WorkflowDetailsController(http.Controller):
    @http.route('/api/workflow/get-workflow-users', type='json', auth='user', methods=['POST'], csrf=False)
    def get_workflow_details(self, **kwargs):
        """
        API to fetch workflow details and associated users.

        :param hash_key: Hash key of the workflow.
        :return: JSON response with workflow details and user information.
        """
        try:
            # Extract inputs
            user = request.env.user
            user_id = user.id
            hash_key = kwargs.get('hash_key')

            if not hash_key:
                return {"success": False, "message": "Hash key is required"}

            # Fetch workflow by hash key and user ID
            workflow = request.env['workflow'].sudo().search([('hash_key', '=', hash_key), ('user_id', '=', user_id)], limit=1)
            if not workflow:
                return {"success": False, "message": "Invalid hash key"}

            # Fetch workflow users
            workflow_users = request.env['workflow.users'].sudo().search([('workflow_id', '=', workflow.id)])
            if not workflow_users:
                return {"success": False, "message": "No users found"}

            # Enrich user details
            user_data = []
            for user_item in workflow_users:
                user_info = {
                    "user_id": user_item.user_id,
                    "id": user_item.id,
                    "is_working": user_item.is_working,
                    "workflow_id": user_item.workflow_id,
                    "first_name": "",
                    "last_name": "",
                }
                # Fetch user details
                user_details = request.env['res.users'].sudo().search([('login', '=', user_item.user_id)], limit=1)
                if user_details:
                    user_info["first_name"] = user_details.name
                else:
                    # Fetch contact details
                    contact_details = request.env['res.partner'].sudo().search([
                        ('email', '=', user_item.user_id),
                    ], limit=1)
                    if contact_details:
                        user_info["first_name"] = contact_details.name

                user_data.append(user_info)

            return {
                "success": True,
                "data": user_data,
            }

        except Exception as e:
            _logger.error(f"Error fetching workflow details: {str(e)}")
            return {
                "success": False,
                "message": f"An error occurred: {str(e)}",
            }
