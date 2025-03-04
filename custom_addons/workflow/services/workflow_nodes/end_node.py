from datetime import datetime
from odoo.addons.workflow.services.helpers import WorkflowHelper
from odoo.addons.workflow.services.email_template import mail_data
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)
workflow_helper = WorkflowHelper()

class EndNode:
    def handle_end_node(self, workflow, node, sub_id):
        """
        Handle the end node in the workflow.

        :param workflow: Workflow record.
        :param node: Node data.
        :param sub_id: Submission ID.
        """
        try:
            _logger.info(f"{workflow.id} ***endflow*** {node['data'].get('endOption')}")
            
            completed = node["data"].get("endOption") != 1

            # Retrieve the workflow JSON
            workflow_data = workflow_helper.get_workflow_json(
                workflow.user_id, 
                workflow.workflow_json
            )
            nodes = workflow_data.get("nodes", [])
            edges = workflow_data.get("edges", [])

            # Count terminal and end-flow nodes
            term_count = sum(
                1 for nd in nodes
                if nd["type"] == "endFlow" and nd["data"].get("endOption") != 1
            )
            end_count = sum(
                1 for nd in nodes
                if nd["type"] == "endFlow" and nd["data"].get("endOption") == 1
            )

            if not completed and end_count == 1 and term_count == 0:
                completed = True

            # Add activity log
            aData = {
                "type": "workflow-complete" if completed else "branch-complete",
                "message": f"{'Workflow' if completed else 'A branch'} was completed.",
                "workflow_id": workflow.id,
                "node_id": node["id"],
                "submission_id": sub_id,
            }
            workflow_helper.add_activity_log(aData)

        except Exception as e:
            _logger.error(f"Error in handle_end_node: {str(e)}")