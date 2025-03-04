import logging
from odoo import http
from odoo.http import request
from odoo.addons.workflow.services.helpers import WorkflowHelper
from odoo.addons.workflow.services.email_template import mail_data

_logger = logging.getLogger(__name__)
workflow_helper = WorkflowHelper()

class WorkflowController(http.Controller):
    @http.route('/api/workflow/reassign', type='json', auth='user', methods=['POST'], csrf=False)
    def reassign_approve_task(self, **kwargs):
        """
        API to reassign an approval task to another user.

        :param id: ID of the approval task.
        :param email: New approver's email address.
        :return: JSON response with success or failure status.
        """
        try:
            # Validate inputs
            approver_id = kwargs.get('id')
            new_email = kwargs.get('email')
            if not approver_id or not new_email:
                return {"success": False, "message": "ID and email are required"}

            # Get the current user
            current_user = request.env.user

            # Fetch the existing approval task
            workflow_approve = request.env['workflow.approves'].sudo().search([('id', '=', approver_id)], limit=1)
            if not workflow_approve:
                return {"success": False, "message": "Approval task not found"}

            old_email = workflow_approve.approver

            # Update the approver
            workflow_approve.write({'approver': new_email})

            # Fetch the associated workflow
            workflow = request.env['workflow'].sudo().search([('id', '=', workflow_approve.workflow_id.id)], limit=1)
            if not workflow:
                return {"success": False, "message": "Workflow not found"}

            # Generate email link and content
            base_url = workflow_helper.generate_dynamic_url("workflow.page.approvals")
            mail_data(
                email_type="workflow_assign", 
                subject=f"You received an invitation to review submitted data for Workflow - #{workflow.name}", 
                email_to=new_email, 
                header=f"Hello {new_email},", 
                description=f"You are assigned to review submitted data for Workflow - #{workflow.name}.",
                base_url=base_url
            )

            # Log activity
            activity_log_data = {
                "type": "approve-reassign",
                "message": f"Workflow reassigned an approve task to {new_email} from {old_email}.",
                "workflow_id": workflow.id,
            }
            workflow_helper.add_activity_log(activity_log_data)

            return {"success": True, "message": "Success to reassign"}

        except Exception as e:
            _logger.error(f"Error in reassign_approve_task: {str(e)}")
            return {"success": False, "message": f"An error occurred: {str(e)}"}
