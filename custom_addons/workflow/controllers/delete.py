from odoo import http
from odoo.http import request
import logging
from datetime import datetime
from odoo.addons.workflow.services.helpers import WorkflowHelper

_logger = logging.getLogger(__name__)
workflow_helper = WorkflowHelper()
class WorkflowController(http.Controller):
    @http.route('/api/workflow/delete', type='json', auth='user', methods=['POST'], csrf=False)
    def delete_workflow(self, **kwargs):
        """
        API to delete a workflow.

        :param workflow_id: ID of the workflow to delete.
        """
        try:
            # Extract inputs
            workflow_id = kwargs.get('workflow_id')
            if not workflow_id:
                return {
                    "success": False,
                    "message": "Workflow ID is required."
                }

            # Fetch workflow details
            workflow = request.env['workflow'].sudo().search([('id', '=', workflow_id)], limit=1)
            if not workflow:
                return {
                    "success": False,
                    "message": "Workflow not found."
                }

            # Delete the workflow and related data
            # workflow_name = workflow.project_name
            workflow_helper.delete_workFlow_data(workflow.id)

            # Notify workflow users about the deletion
            # self._notify_workflow_users(workflow_id, request.env.user.login)

            # Audit log
            # user = request.env.user
            # ip_address = request.httprequest.remote_addr
            # self._add_audit_log(
            #     user.id,
            #     f"You deleted workflow <b>{workflow_name}</b> from IP: <b>{ip_address}</b>",
            #     'workflow',
            #     datetime.now()
            # )

            return {
                "success": True,
                "message": "Workflow has been deleted successfully."
            }

        except Exception as e:
            _logger.error(f"Error in delete_workflow: {str(e)}")
            return {
                "success": False,
                "message": f"An error occurred: {str(e)}"
            }

    # def _notify_workflow_users(self, workflow_id, email):
    #     """
    #     Notify users associated with the workflow about its deletion.

    #     :param workflow_id: ID of the workflow.
    #     :param email: Email of the user performing the deletion.
    #     """
    #     try:
    #         # Logic to notify users (if required)
    #         workflow_users = request.env['workflow.users'].sudo().search([('workflow_id', '=', workflow_id)])
    #         for user in workflow_users:
    #             request.env['mail.mail'].sudo().create({
    #                 "subject": "Workflow Deleted",
    #                 "body_html": f"The workflow has been deleted by {email}.",
    #                 "email_to": user.user_id,
    #             }).send()

    #             mail_data(
    #                 email_type="delete_workflow", 
    #                 subject=f"Workflow Deleted",  
    #                 email_to=email,
    #                 header=f"Hi {receiver_user.name},", 
    #                 description=f"You are requested by <b>{user_details.name}</b> to sign this document.",
    #                 hash_key=hash_link,
    #             )
    #     except Exception as e:
    #         _logger.error(f"Error notifying workflow users: {str(e)}")

    # def _add_audit_log(self, user_id, message, log_type, timestamp):
    #     """
    #     Add an audit log entry.

    #     :param user_id: ID of the user.
    #     :param message: Log message.
    #     :param log_type: Type of log.
    #     :param timestamp: Timestamp of the event.
    #     """
    #     try:
    #         request.env['audit.log'].sudo().create({
    #             "user_id": user_id,
    #             "message": message,
    #             "type": log_type,
    #             "timestamp": timestamp,
    #         })
    #     except Exception as e:
    #         _logger.error(f"Error adding audit log: {str(e)}")
