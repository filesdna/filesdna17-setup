import logging
from odoo import http
from odoo.http import request
from odoo.addons.workflow.services.helpers import WorkflowHelper
import json
from datetime import datetime, date

_logger = logging.getLogger(__name__)
workflow_helper = WorkflowHelper()

def custom_serializer(obj):
    """
    Custom JSON serializer for objects not serializable by default json code
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()  # Convert to ISO format (e.g., 'YYYY-MM-DDTHH:MM:SS')
    elif isinstance(obj, bytes):
        return obj.decode('utf-8')  # Decode bytes to string
    raise TypeError(f"Type {type(obj)} not serializable")

class WorkflowDetailsController(http.Controller):
    @http.route('/api/workflow/get-details', type='http', auth='user', methods=['POST'], csrf=False)
    def get_workflow_details(self, **kwargs):
        try:
            # Parse JSON payload if Content-Type is application/json
            if request.httprequest.content_type == 'application/json':
                kwargs = json.loads(request.httprequest.data.decode('utf-8'))
            
            _logger.info(f"kwargs: {kwargs}")
            # Validate user
            if not request.env.user:
                return request.make_response(
                    json.dumps({"success": False, "message": "Invalid User"}),
                    headers={"Content-Type": "application/json"}
                )

            # Extract inputs
            hash_key = kwargs.get('hash_key')
            if not hash_key:
                return request.make_response(
                    json.dumps({"success": False, "message": "Hash key is required"}),
                    headers={"Content-Type": "application/json"}
                )

            user = request.env.user
            user_id = user.id

            # Fetch workflow project
            workflow = request.env['workflow'].sudo().search([
                ('type', '=', 'workflow'),
                ('hash_key', '=', hash_key)
            ], limit=1)

            if not workflow:
                return request.make_response(
                    json.dumps({"success": False, "message": "Invalid hash key"}),
                    headers={"Content-Type": "application/json"}
                )

            # Fetch additional user and workflow data
            forms = request.env['smart.form'].sudo().search([
                ('user_id', '=', user_id),
                ('is_trash', '=', False),
                ('type', '=', 'form')
            ])

            contacts = request.env['workflow.users'].sudo().search([
                ('workflow_id', '=', workflow.id)
            ])

            templates = request.env['dms.file'].sudo().search([
                ('is_template', '=', True),
                ('is_deleted', '=', False)
            ])
            template_fields = ['id', 'name', 'is_template', 'create_date','sha512_hash','current_time_seconds']
            templates_data = templates.read(template_fields)
            for template in templates_data:
                sha512_hash = template.get('sha512_hash')  # Assuming 'sha512_hash' exists
                current_time_seconds = template.get('current_time_seconds')
                if sha512_hash:
                    template['hash_url'] = f"{sha512_hash}-{current_time_seconds}"
            # Append related data to workflow
            workflow_data = {
                "id": workflow.id,
                "name": workflow.name,
                "status": workflow.status,
                "restart": workflow.restart,
                "folder": workflow.folder,
                "type": workflow.type,
                "current_doc":workflow.current_doc,
                "current_form":workflow.current_form,
                "createdat": workflow.create_date.isoformat(),
                "updatedat": workflow.write_date.isoformat(),
                "hash_key": workflow.hash_key,
                "user_id": workflow.user_id,
                "workflow_json": workflow.workflow_json,
            }
            workflow_data.update({
                "forms": forms.read(),
                "contacts": contacts.read(),
                "templates": templates_data,
            })

            # Add workflow JSON data for the owner
            if workflow.workflow_json:
                workflow_data['workflow_json'] = WorkflowHelper().get_workflow_json(
                    user_id,
                    workflow.workflow_json
                )

            # Use the custom serializer to handle datetime and bytes objects
            return request.make_response(
                json.dumps({"success": True, "data": workflow_data}, default=custom_serializer),
                headers={"Content-Type": "application/json"}
            )

        except Exception as e:
            _logger.error(f"Error fetching workflow details: {str(e)}")
            return request.make_response(
                json.dumps({"success": False, "message": f"An error occurred: {str(e)}"}),
                headers={"Content-Type": "application/json"}
            )
