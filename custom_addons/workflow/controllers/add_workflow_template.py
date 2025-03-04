from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class WorkflowTemplateController(http.Controller):
    @http.route('/api/workflow/add-template-workflow', type='json', auth='user', methods=['POST'], csrf=False)
    def add_workflow_template(self, **kwargs):
        """
        API to add or update a workflow template.

        :param workflow_id: ID of the workflow.
        :param template_id: ID of the template.
        :param roles: Roles associated with the template.
        :param status: Status of the template (default: Completed).
        :param document_id: ID of the document.
        :param document_hash_url: Hash URL of the document.
        :param is_completed: Boolean indicating if the template is completed (default: true).
        :param node_id: ID of the workflow node.
        :param submission_id: Submission ID.
        :return: JSON response indicating success or failure.
        """
        try:
            workflow_id = kwargs.get('workflow_id')
            template_id = kwargs.get('template_id')
            roles = kwargs.get('roles')
            status = kwargs.get('status', 'Completed')
            document_id = kwargs.get('document_id')
            document_hash_url = kwargs.get('document_hash_url')
            is_completed = kwargs.get('is_completed', 'true')
            node_id = kwargs.get('node_id')
            submission_id = kwargs.get('submission_id')

            if not workflow_id or not template_id or not submission_id:
                return {"success": False, "message": "Missing required parameters."}

            # Check if the template already exists
            existing_template = request.env['workflow.templates'].sudo().search([
                ('workflow_id', '=', workflow_id),
                ('template_id', '=', template_id),
                ('submission_id', '=', submission_id),
                ('node_id', '=', node_id),
            ], limit=1)

            if not existing_template:
                # Create a new template
                request.env['workflow.templates'].sudo().create({
                    'workflow_id': workflow_id,
                    'template_id': template_id,
                    'roles': roles,
                    'status': status,
                    'document_id': document_id,
                    'is_completed': is_completed,
                    'node_id': node_id,
                    'submission_id': submission_id,
                })
            else:
                # Update the existing template
                existing_template.write({
                    'workflow_id': workflow_id,
                    'template_id': template_id,
                    'roles': roles,
                    'status': status,
                    'document_id': document_id,
                    'is_completed': is_completed,
                    'node_id': node_id,
                    'submission_id': submission_id,
                })

            _logger.info(f"created the template successfully")
            return {"success": True, "message": "Workflow template added/updated successfully."}

        except Exception as e:
            _logger.error(f"Error in add_workflow_template: {str(e)}")
            return {"success": False, "message": f"An error occurred: {str(e)}"}
