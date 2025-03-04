from datetime import datetime
from odoo.addons.workflow.services.helpers import WorkflowHelper
from odoo.addons.workflow.services.email_template import mail_data
from odoo.http import request
import logging
import json

_logger = logging.getLogger(__name__)
workflow_helper = WorkflowHelper()

class IfElseNode:
    def handle_if_else_node(self, workflow, node, sub_id):
        """
        Handle If-Else Node in the Workflow.

        :param workflow: Workflow record.
        :param node: Node data containing conditions and combine rule.
        :param sub_id: Submission ID.
        """
        try:
            conditions = node["data"].get("conditions", [])
            combine = node["data"].get("combine")
            result = []

            for con in conditions:
                _logger.info("Processing condition: %s, combine: %s", con, combine)
                if_value = (
                    workflow_helper.get_field_value_placeholder(con["if"], sub_id, con.get("customFieldOption"))
                    if con.get("customFieldOption")
                    else workflow_helper.get_field_value(con["if"], sub_id)
                )

                _logger.info("Evaluated if_value: %s", if_value)

                if con["state"] == "empty":
                    result.append(if_value == "")
                elif con["state"] == "filled":
                    result.append(if_value != "")
                else:
                    target_value = (
                        sorted(con["value"]) if isinstance(con["value"], list) else con["value"]
                        if con["target"] == "value"
                        else workflow_helper.get_field_value(con["target"], sub_id)
                    )

                    if con["state"] == "equal":
                        result.append(if_value == target_value)
                    elif con["state"] == "not-equal":
                        result.append(if_value != target_value)
                    elif con["state"] == "less":
                        result.append(float(if_value) < float(target_value))
                    elif con["state"] == "greater":
                        result.append(float(if_value) > float(target_value))
                    elif con["state"] == "contain":
                        result.append(
                            target_value.lower() in if_value.lower()
                        )

                    _logger.info(
                        "if_value: %s | target_value: %s | state: %s",
                        if_value,
                        target_value,
                        con["state"]
                    )

            if len(result) == 1:
                status = "YES" if result[0] else "NO"
            else:
                if combine == "all":
                    status = "NO" if any(not r for r in result) else "YES"
                else:
                    status = "YES" if any(result) else "NO"

            activity_data = {
                "type": "workflow-condition",
                "message": f'Workflow passed an IfElse condition task with "{status}".',
                "workflow_id": workflow.id,
                "node_id": node["id"],
                "submission_id": sub_id,
            }
            workflow_helper.add_activity_log(activity_data)
            return status
        except Exception as e:
            _logger.error("Error in handle_if_else_node: %s", str(e))