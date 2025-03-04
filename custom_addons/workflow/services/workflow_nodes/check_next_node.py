from datetime import datetime
from odoo.addons.workflow.services.helpers import WorkflowHelper
from odoo.addons.workflow.services.email_template import mail_data

from odoo.addons.workflow.services.workflow_nodes.approval_node import ApprovalNode
from odoo.addons.workflow.services.workflow_nodes.approval_report_node import ApprovalReportNode
from odoo.addons.workflow.services.workflow_nodes.end_node import EndNode
from odoo.addons.workflow.services.workflow_nodes.form_node import FormNode
from odoo.addons.workflow.services.workflow_nodes.if_else_node import IfElseNode
from odoo.addons.workflow.services.workflow_nodes.conditional_node import ConditionalNode

from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

#Helper
workflow_helper = WorkflowHelper()

#Nodes
approval_node = ApprovalNode()
approval_report_node = ApprovalReportNode()
end_node = EndNode()
form_node = FormNode()
if_else_node = IfElseNode()
conditional_node = ConditionalNode()

class CheckNextNode:
    def check_next_step(self, workflow, node_id, status, sub_id):
        """
        Check the next step in the workflow and handle the corresponding node.

        :param workflow: Workflow record.
        :param node_id: Current node ID.
        :param status: Status to determine the next step.
        :param sub_id: Submission ID.
        """
        try:
            _logger.info(f"{workflow.id} ***** check step **** {node_id} {status} {sub_id}")

            next_nodes = workflow_helper.get_next_nodes(workflow, node_id)

            for node in next_nodes:
                _logger.info(f"***** node **** {node}")

                if node["type"] == "endFlow":
                    end_node.handle_end_node(workflow, node, sub_id)
                elif node["type"] == "outcome" and status == node["data"].get("label"):
                    self.check_next_step(workflow, node["id"], None, sub_id)
                elif node["type"] == "email":
                    self.handle_email_node(workflow, node, sub_id)
                elif node["type"] in ["approval", "approveSign", "teamApproval"]:
                    approval_node.handle_approval_node(workflow, node, sub_id)
                elif node["type"] == "form":
                    form_node.handle_form_node(workflow, node, sub_id)
                elif node["type"] == "ifElseCondition":
                    stats = if_else_node.handle_if_else_node(workflow, node, sub_id)
                    self.check_next_step(workflow, node["id"], stats, sub_id)
                elif node["type"] == "conditionalBranch":
                    branch = conditional_node.handle_conditional_node(workflow, node, sub_id)
                    self.check_next_step(workflow, node["id"], branch, sub_id)
                elif node["type"] == "approvalReport":
                    approval_report_node.handle_approval_report(workflow, node, sub_id)
                    self.check_next_step(workflow, node["id"], None, sub_id)
                elif node["type"] in ["splitBranch", "mergeBranch"]:
                    self.check_next_step(workflow, node["id"], None, sub_id)

        except Exception as e:
            _logger.error(f"Error in check_next_step: {str(e)}")


    def handle_email_node(self, workflow, node, sub_id):
        """
        Handle an email node in the workflow.

        :param workflow: Workflow record.
        :param node: Node data.
        :param sub_id: Submission ID.
        """
        try:
            email_value = None
            if node["data"].get("clientEmail"):
                submission = request.env["submission"].sudo().search([("id", "=", sub_id)], limit=1)
                email_data = [
                    sub for sub in json.loads(submission.data)
                    if sub.get("type") == "email"
                ]
                email_value = email_data[0]["value"] if email_data else None

            email_to = node["data"].get("clientEmail", email_value) or node["data"].get("recipientEmail")
            subject = f"{node['data'].get('subject', 'Workflow Email')} from {node['data'].get('senderName', '')}"
            content = node["data"].get("content", "Workflow Email")

            # Send email
            mail_data(
                email_type="workflow_email", 
                subject=subject, 
                email_to=email_to, 
                header=f"Hello There,", 
                description=f"",
                content=content
            )

            # Log the activity
            a_data = {
                "type": "workflow-email",
                "message": f"Workflow sent an email to {email_to}.",
                "workflow_id": workflow.id,
                "node_id": node["id"],
                "submission_id": sub_id,
            }
            workflow_helper.add_activity_log(a_data)

            # Continue to the next step
            self.check_next_step(workflow, node["id"], None, sub_id)

        except Exception as e:
            _logger.error(f"Error in handle_email_node: {str(e)}")
