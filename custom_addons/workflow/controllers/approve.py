from odoo import http
from odoo.http import request
import json
import logging
from odoo.addons.workflow.services.workflow_nodes.check_next_node import CheckNextNode
_logger = logging.getLogger(__name__)

check_next_node = CheckNextNode()
class WorkflowApproveController(http.Controller):
    @http.route('/api/workflow/approve', type='json', auth='user', methods=['POST'], csrf=False)
    def approve_document(self, **kwargs):
        """
        API to approve a document in the workflow.

        :param id: Approval ID.
        :param comment: Comment for the approval.
        :param signature: JSON data for the signature.
        :param status: Approval status.
        :param sub_id: Submission ID.
        :return: JSON response with success or error message.
        """
        try:
            # Extract inputs
            approval_id = kwargs.get('id')
            comment = kwargs.get('comment')
            signature = kwargs.get('signature')
            status = kwargs.get('status')
            submission_id = kwargs.get('sub_id')

            if not approval_id or not status or not submission_id:
                return {"success": False, "message": "Missing required parameters."}

            # Fetch and update approval record
            approval = request.env['workflow.approves'].sudo().search([('id', '=', approval_id)], limit=1)
            if not approval:
                return {"success": False, "message": "Approval record not found."}

            approval.write({
                'comment': comment,
                'signature': signature,
                'status': status,
            })

            # Fetch related workflow
            workflow = request.env['workflow'].sudo().search([('id', '=', approval.workflow_id.id)], limit=1)
            if not workflow:
                return {"success": False, "message": "Workflow not found."}

            # Log activity
            activity_data = {
                "type": "approve-select",
                "message": f"Approver {request.env.user.login} selected outcome '{status}' for {approval.type} task #{approval.id}.",
                "workflow_id": workflow.id,
                "node_id": approval.node_id,
                "submission_id": submission_id,
            }
            request.env['workflow.activity'].sudo().create(activity_data)

            # Process approval outcomes
            outcomes = json.loads(approval.outcomes or '[]')
            approver_count = request.env['workflow.approves'].sudo().search_count([
                ('workflow_id', '=', workflow.id),
                ('node_id', '=', approval.node_id),
                ('submission_id', '=', submission_id),
            ])
            response_count = request.env['workflow.approves'].sudo().search_count([
                ('workflow_id', '=', workflow.id),
                ('node_id', '=', approval.node_id),
                ('submission_id', '=', submission_id),
                ('status', '!=', 'pending'),
            ])

            outcome_counts = {
                outcome['title']: request.env['workflow.approves'].sudo().search_count([
                    ('workflow_id', '=', workflow.id),
                    ('node_id', '=', approval.node_id),
                    ('submission_id', '=', submission_id),
                    ('status', '=', outcome['title']),
                ])
                for outcome in outcomes
            }
            max_outcome = max(outcome_counts, key=outcome_counts.get)

            # Check next step based on rules
            rule = approval.rule or 'o'
            if rule == 'o' or not rule:
                check_next_node.check_next_step(workflow, approval.node_id, max_outcome, submission_id)
            elif rule == 'a' and approver_count == response_count:
                check_next_node.check_next_step(workflow, approval.node_id, max_outcome, submission_id)
            elif rule == 'm' and (approver_count / 2 <= response_count):
                check_next_node.check_next_step(workflow, approval.node_id, max_outcome, submission_id)

            return {
                "success": True,
                "message": "Success to approve workflow",
                "data": workflow.id,
            }

        except Exception as e:
            _logger.error(f"Error in approve_document: {str(e)}")
            return {"success": False, "message": f"An error occurred: {str(e)}"}
