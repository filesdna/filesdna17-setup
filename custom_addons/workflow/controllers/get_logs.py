import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class WorkflowLogsController(http.Controller):
    @http.route('/api/workflow/get-logs', type='json', auth='user', methods=['POST'], csrf=False)
    def get_workflow_logs(self, **kwargs):
        """
        API to fetch workflow logs.

        :param hash_key: Hash key of the workflow.
        :return: JSON response with workflow logs.
        """
        try:
            # Validate user
            if not request.env.user:
                return {"success": False, "message": "Invalid user"}

            # Extract inputs
            hash_key = kwargs.get('hash_key')
            if not hash_key:
                return {"success": False, "message": "Hash key is required"}

            # Find the workflow
            workflow = request.env['workflow'].sudo().search([('hash_key', '=', hash_key)], limit=1)
            if not workflow:
                return {"success": False, "message": "Workflow not found"}

            # Fetch logs for the workflow
            logs = request.env['workflow.activity'].sudo().search([('workflow_id', '=', workflow.id)])
            
            # Prepare logs data
            logs_data = [
                {
                    'id': log.id,
                    'workflow_id': log.workflow_id.id,
                    'message': log.message,
                    'type': log.type,
                    'node_id': log.node_id,
                    'submission_id': log.submission_id,
                    'createdat': log.create_date,
                    'updatedat': log.write_date,
                }
                for log in logs
            ]

            return {
                "success": True,
                "data": logs_data,
            }

        except Exception as e:
            _logger.error(f"Error fetching workflow logs: {str(e)}")
            return {
                "success": False,
                "message": f"An error occurred: {str(e)}",
            }
