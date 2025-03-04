from datetime import datetime
from odoo import fields  # Added this import
from odoo.addons.workflow.services.helpers import WorkflowHelper
from odoo.addons.workflow.services.email_template import mail_data
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)
workflow_helper = WorkflowHelper()

class ApprovalReportNode:
    def handle_approval_report(self, workflow, node, sub_id):
        """
        Handle Approval Report in Workflow.

        :param workflow: Workflow record.
        :param node: Node data.
        :param sub_id: Submission ID.
        """
        try:
            report_name = node["data"].get("reportName")
            recipient_email = node["data"].get("recipientEmail")
            report_comment = node["data"].get("reportComment")

            # Prepare activity log data
            activity_data = {
                "type": "approval-report",
                "message": f'Workflow sent an approval report "{report_name}" to {recipient_email}.',
                "workflow_id": workflow.id,
                "node_id": node["id"],
                "submission_id": sub_id,
            }

            # Retrieve existing workflow activities
            activities = request.env["workflow.activity"].sudo().search([("workflow_id", "=", workflow.id)])
            activity_records = activities.read(["type", "message", "create_date"])
            activity_records.append(activity_data)

            # Generate email content
            content = (
                f"<style>table.approval-report-table td{{ border: 1px solid lightgray; padding: 5px; }}</style>"
                f"<h2>{report_name} from Workflow \"{workflow.name}\"</h2><hr>"
                f"<p>{report_comment}</p><hr>"
                f"<h4>FLOW ACTIVITY HISTORY</h4>"
                f"<table class='approval-report-table'>"
                f"<tr><td>Type</td><td>Action</td><td>Date</td></tr>"
            )
            for activity in activity_records:
                activity_date = fields.Datetime.to_string(activity["create_date"]) if "create_date" in activity else ""
                content += f"<tr><td>{activity['type']}</td><td>{activity['message']}</td><td>{activity_date}</td></tr>"
            content += "</table>"

            # Send email
            mail_data(
                email_type="workflow_report_approval", 
                subject=report_name, 
                email_to=recipient_email, 
                header=f"Hello There,", 
                description=f"",
                content=content
            )

            # Log activity
            workflow_helper.add_activity_log(activity_data)

        except Exception as e:
            _logger.error("Error in handle_approval_report: %s", str(e))