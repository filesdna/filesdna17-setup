from datetime import datetime
from odoo.addons.workflow.services.helpers import WorkflowHelper
from odoo.addons.workflow.services.email_template import mail_data
from odoo.http import request
import logging
import os
import json

_logger = logging.getLogger(__name__)
workflow_helper = WorkflowHelper()

class ApprovalNode:
    def handle_approval_node(self, workflow, node, sub_id):
        try:
            """
            Handles the approval node in a workflow.

            :param workflow: Workflow record
            :param node: Node data dictionary
            :param sub_id: Submission ID
            """
            # Get submission and form
            sub_and_form = workflow_helper.get_sub_and_form(sub_id)
            submission = sub_and_form.get('submission')
            form = sub_and_form.get('form')            
            approvers = node.get("data", {}).get("approvers", [])
            _logger.info(f"form_id:{form}")
            for approver in approvers:
                # Create approval record
                request.env["workflow.approves"].sudo().create({
                    "workflow_id": workflow.id,
                    "form_id": form.id,
                    "node_id": node["id"],
                    "type": node["type"],
                    "status": "pending",
                    "outcomes": json.dumps(node["data"].get("outcomes", [])),
                    "approver": approver,
                    "rule": node["data"].get("completionRule"),
                    "notify": node["data"].get("notify"),
                    "require_login": node["data"].get("requireLogin"),
                    "reassign": node["data"].get("reassign"),
                    "require_comment": node["data"].get("requireComments"),
                    "escalate": node["data"].get("escalation"),
                    "escalate_date": node["data"].get("escalateDate"),
                    "escalate_email": node["data"].get("escalateEmail"),
                    "auto_finish": node["data"].get("autoFinish"),
                    "auto_finish_date": node["data"].get("autoFinishDate"),
                    "auto_finish_outcome": node["data"].get("autoFinishOutcome"),
                    "submission_id": sub_id,
                })

                # Prepare link
                base_url = workflow_helper.generate_dynamic_url("workflow.page.approvals")
                mail_data(
                    email_type="workflow_assign", 
                    subject=f"You received an invitation to review submitted data for Workflow - {workflow.name}", 
                    email_to=approver, 
                    header=f"Hello {approver.split('@')[0]},", 
                    description=f"You are assigned to review submitted data for Workflow - {workflow.name}.",
                    base_url=base_url
                )

                # Add notification
                # if email_data:
                #     self.env["notification.log"].sudo().create({
                #         "type": "approve-workflow",
                #         "user_id": email_data.id,
                #         "message": f"You received an invitation to review submitted data for Workflow - {workflow.name}",
                #         "title": f"Workflow Approve - {workflow.name}",
                #     })

            # Add activity log
            activity_log = {
                "type": "approve-assign",
                "message": f"Workflow assigned an approve task to {', '.join(approvers)}.",
                "workflow_id": workflow.id,
                "node_id": node["id"],
                "submission_id": sub_id,
            }
            workflow_helper.add_activity_log(activity_log)
        except Exception as e:
            _logger.error(f"Error in handle approval: {str(e)}")

