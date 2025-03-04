import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class WorkflowTemplateController(http.Controller):
    @http.route('/api/workflow/get-template-workflow', type='json', auth='user', methods=['POST'], csrf=False)
    def get_workflow_template(self, **kwargs):
        """
        API to fetch workflow templates.

        :param workflow_id: ID of the workflow.
        :return: JSON response with workflow templates.
        """
        try:
            # Extract inputs
            workflow_id = kwargs.get('workflow_id')
            if not workflow_id:
                return {"success": False, "message": "Workflow ID is required"}

            # Find templates associated with the workflow
            templates = request.env['workflow.template'].sudo().search([('workflow_id', '=', workflow_id)])
            if not templates:
                return {"success": False, "message": "Template not found"}

            # Prepare response data
            template_data = templates.read()

            return {
                "success": True,
                "data": template_data,
            }

        except Exception as e:
            _logger.error(f"Error fetching workflow templates: {str(e)}")
            return {
                "success": False,
                "message": f"An error occurred: {str(e)}",
            }
