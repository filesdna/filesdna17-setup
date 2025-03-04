import logging
from odoo import http
from odoo.http import request
from datetime import datetime
from odoo.addons.workflow.services.helpers import WorkflowHelper

_logger = logging.getLogger(__name__)
workflow_helper = WorkflowHelper()

class WorkflowCompleteController(http.Controller):
    @http.route('/api/workflow/complete', type='json', auth='user', methods=['POST'], csrf=False)
    def update_project_status(self, **kwargs):
        """
        API to change the status of a project workflow.

        :param hash_key: Unique identifier for the workflow.
        :return: JSON response with success or failure message.
        """
        try:
            # Validate user
            if not request.env.user:
                return {"success": False, "message": "Invalid user."}

            user_id = request.env.user.id
            hash_key = kwargs.get('hash_key')

            if not hash_key:
                return {"success": False, "message": "Missing required parameters."}

            # Fetch the workflow
            workflow = request.env['workflow'].sudo().search([('hash_key', '=', hash_key), ('user_id', '=', user_id)], limit=1)

            if not workflow:
                return {"success": False, "message": "No project found."}

            # Update workflow status
            workflow.write({'status': 'Completed'})

            # Add activity log
            data = {
                'type': 'completed',
                'message': "Workflow has been completed by you",
                'workflow_id': workflow.id,
            }

            workflow_helper.add_activity_log(data)

            # Notify workflow users
            # request.env['workflow.notification'].sudo().send_to_users(
            #     workflow.id,
            #     {"type": "update_workflow_shared_list"},
            #     request.env.user.email
            # )

            # Log audit event
            # user_ip = request.env['res.users'].sudo().get_user_ip(request.httprequest)
            # request.env['workflow.audit.log'].sudo().create({
            #     'user_id': user_id,
            #     'message': f"You completed workflow <b>{workflow.name}</b> from IP: <b>{user_ip}</b>",
            #     'event_type': 'workflow',
            # })

            return {
                "success": True,
                "message": "Workflow has been completed! Thank you",
            }

        except Exception as e:
            _logger.error(f"Error updating project status: {str(e)}")
            return {"success": False, "message": f"An error occurred: {str(e)}"}
