from datetime import datetime
from odoo.addons.workflow.services.helpers import WorkflowHelper
from odoo.addons.workflow.services.email_template import mail_data
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)
workflow_helper = WorkflowHelper()

class ConditionalNode:
    def handle_conditional_node(self, workflow, node, sub_id):
        """
        Handle Conditional Node in Workflow.

        :param workflow: Workflow record.
        :param node: Node data containing branches and type.
        :param sub_id: Submission ID.
        """
        try:
            branches = node["data"].get("branches", [])
            node_type = node["data"].get("type")
            branch = None

            for branch_data in branches:
                conditions = branch_data.get("conditions", [])
                combine = branch_data.get("combine")
                name = branch_data.get("name")
                _logger.info("branch_data: %s", name)

                if node_type == "form":
                    result = []
                    for condition in conditions:
                        field_value = workflow_helper.get_field_value(condition["if"], sub_id)

                        if condition["state"] == "empty":
                            result.append(field_value == "")
                        elif condition["state"] == "filled":
                            result.append(field_value != "")
                        else:
                            target_value = (
                                sorted(condition["value"]) if isinstance(condition["value"], list) else condition["value"]
                                if condition["target"] == "value"
                                else workflow_helper.get_field_value(condition["target"], sub_id)
                            )

                            if condition["state"] == "equal":
                                result.append(field_value == target_value)
                            elif condition["state"] == "not-equal":
                                result.append(field_value != target_value)
                            elif condition["state"] == "less":
                                result.append(float(field_value) < float(target_value))
                            elif condition["state"] == "greater":
                                result.append(float(field_value) > float(target_value))
                            elif condition["state"] == "contain":
                                result.append(target_value.lower() in field_value.lower())

                            _logger.info(
                                "Field Value: %s | Target Value: %s | State: %s",
                                field_value,
                                target_value,
                                condition["state"],
                            )

                    status = (
                        "YES" if result[0] else "NO"
                        if len(result) == 1
                        else (
                            "NO" if any(not r for r in result) else "YES"
                            if combine == "all"
                            else "YES" if any(result) else "NO"
                        )
                    )
                    if not branch and status == "YES":
                        branch = name
                else:
                    # Processing for non-form type
                    template_ids = [
                        int(condition["if"].replace("template-", ""))
                        for condition in conditions
                    ]
                    _logger.info("template_ids: %s", template_ids)

                    document_states = [condition["state"] for condition in conditions]
                    _logger.info("document_states: %s", document_states)

                    matching_templates = request.env["workflow.templates"].sudo().search([
                        ("template_id", "in", template_ids),
                        ("submission_id", "=", sub_id),
                    ])
                    _logger.info("matching_templates: %s", matching_templates)

                    document_ids = [int(template.document_id) for template in matching_templates]
                    _logger.info("document_ids: %s", document_ids)

                    templates = request.env["dms.file"].sudo().search([
                        ("id", "in", document_ids),
                        ("document_status", "in", document_states),
                    ])
                    _logger.info("templates: %s", templates)
                    _logger.info("combine: %s", combine)

                    if (combine == "all" and len(templates) == len(conditions)) or (
                        combine == "any" and len(templates) > 0
                    ):
                        branch = name

            if not branch:
                branch = "Other Option"

            _logger.info("Selected Branch: %s", branch)

            activity_data = {
                "type": "workflow-condition",
                "message": f'Workflow passed a Conditional branch task with "{branch}".',
                "workflow_id": workflow.id,
                "node_id": node["id"],
                "submission_id": sub_id,
            }
            workflow_helper.add_activity_log(activity_data)
            return branch
        except Exception as e:
            _logger.error("Error in handle_conditional_node: %s", str(e))