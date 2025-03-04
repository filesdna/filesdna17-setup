from odoo import http
from odoo.http import request, Response
import logging
import json
from datetime import datetime, date

_logger = logging.getLogger(__name__)

def custom_serializer(obj):
    """
    Custom JSON serializer for objects not serializable by default json code
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()  # Convert to ISO format (e.g., 'YYYY-MM-DDTHH:MM:SS')
    elif isinstance(obj, bytes):
        return obj.decode('utf-8')  # Decode bytes to string
    raise TypeError(f"Type {type(obj)} not serializable")

class WorkflowApprovalsController(http.Controller):
    @http.route('/api/workflow/get-my-approvals', type='http', auth='user', methods=['GET'], csrf=False)
    def get_my_approvals(self):
        """
        API to fetch approvals for the current user.

        :return: JSON response with approval data or an error message.
        """
        try:
            # Get the current user
            user = request.env.user
            user_email = user.login

            # Fetch approvals for the current user
            approvals = request.env['workflow.approves'].sudo().search([('approver', '=', user_email)])

            approval_data = []
            for approval in approvals:
                workflow = request.env['workflow'].sudo().search([('id', '=', approval.workflow_id.id)], limit=1)
                form = request.env['smart.form'].sudo().search([('id', '=', approval.form_id)], limit=1)
                submission = request.env['submission'].sudo().search([('id', '=', approval.submission_id)], limit=1)

                approval_data.append({
                    'id': approval.id,
                    'workflow_id': approval.workflow_id.id,
                    'form_id': approval.form_id,
                    'node_id': approval.node_id,
                    'type': approval.type,
                    'status': approval.status,
                    'outcomes': approval.outcomes,
                    'approver': approval.approver,
                    'rule': approval.rule,
                    'notify': approval.notify,
                    'require_login': approval.require_login,
                    'signature': approval.signature,
                    'comment': approval.comment,
                    'reassign': approval.reassign,
                    'require_comment': approval.require_comment,
                    'escalate': approval.escalate,
                    'escalate_date': approval.escalate_date,
                    'escalate_email': approval.escalate_email,
                    'auto_finish': approval.auto_finish,
                    'auto_finish_date': approval.auto_finish_date,
                    'auto_finish_outcome': approval.auto_finish_outcome,
                    'submission_id': approval.submission_id,
                    'workflow': workflow.read()[0] if workflow else None,
                    'form': form.read()[0] if form else None,
                    'submission': submission.read()[0] if submission else None,
                })

            response_data = {
                "success": True,
                "data": approval_data,
            }
            return Response(
                json.dumps(response_data,default=custom_serializer),
                content_type="application/json",
                status=200
            )

        except Exception as e:
            _logger.error(f"Error in get_my_approvals: {str(e)}")
            response_data = {
                "success": False,
                "message": f"An error occurred: {str(e)}",
            }
            return Response(
                json.dumps(response_data),
                content_type="application/json",
                status=500
            )
