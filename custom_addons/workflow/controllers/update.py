import json
import os
import logging
from odoo import http
from odoo.http import request
from datetime import datetime
from odoo.tools import config
from odoo.addons.workflow.services.google_storage import LocalStorageService
from odoo.addons.workflow.services.helpers import WorkflowHelper
from odoo.addons.workflow.services.workflow_nodes.form_node import FormNode

_logger = logging.getLogger(__name__)

server_path = config['server_path']

workflow_helper = WorkflowHelper()
node_service = FormNode()

class WorkflowUpdateController(http.Controller):
    @http.route('/api/workflow/update', type='json', auth='user', methods=['POST'], csrf=False)
    def update_workflow(self, **kwargs):
        """
        API to update a workflow.

        :param hash_key: Workflow unique identifier.
        :param name: Workflow name.
        :param status: Workflow status.
        :param restart: Restart flag.
        :param workflow_json: Workflow JSON data.
        :return: JSON response with success or failure message.
        """
        try:
            # Validate required fields
            hash_key = kwargs.get('hash_key')
            name = kwargs.get('name')
            status = kwargs.get('status')
            restart = kwargs.get('restart')
            workflow_json = kwargs.get('workflow_json')

            if not hash_key or not name or not workflow_json:
                return {"success": False, "message": "Missing required fields."}

            # Fetch the workflow
            workflow = request.env['workflow'].sudo().search([('hash_key', '=', hash_key)], limit=1)
            if not workflow:
                return {"success": False, "message": "Invalid Project ID."}

            try:
                # Handle the workflow JSON
                json_file = workflow.workflow_json or f"workflow-{int(datetime.now().timestamp())}"
                temp_path = os.path.join('/tmp', f"{json_file}.json")
                
                with open(temp_path, 'w', encoding='utf-8') as temp_file:
                    temp_file.write(workflow_json)

                # Encrypt and upload the JSON file
                key = request.env.user.company_id.encription_key

                gcs_service = LocalStorageService()
                db_name = request.env['ir.config_parameter'].sudo().get_param('web.base.url').split("//")[1].split(".")[0]
                destination = f"{db_name}/workflow/{json_file}.json"
                gcs_service.upload_file(temp_path, destination, key)

                if os.path.exists(temp_path):
                    os.remove(temp_path)

                # Clean up related pending records
                request.env['workflow.emails'].sudo().search([('workflow_id', '=', workflow.id), ('status', '=', 'pending')]).unlink()
                request.env['workflow.forms'].sudo().search([('workflow_id', '=', workflow.id), ('status', '=', 'pending')]).unlink()
                request.env['workflow.approves'].sudo().search([('workflow_id', '=', workflow.id), ('status', '=', 'pending')]).unlink()
                request.env['invite'].sudo().search([('from_user', '=', f"Workflow:{workflow.id}")]).unlink()

                # Update the workflow
                workflow.write({
                    'name': name,
                    'status': status,
                    'restart': restart,
                    'workflow_json': json_file,
                })

                # Log activity
                activity_message = (
                    f"Workflow was published by {request.env.user.name}"
                    if status == "Published"
                    else f"Workflow details updated by {request.env.user.name}"
                )

                data = {
                    'type': "published" if status == "Published" else "updated",
                    'workflow_id': workflow.id,
                    'message': activity_message,
                    }

                workflow_helper.add_activity_log(data)

                # Handle first node for published workflows
                if status == "Published":
                    workflow_data = json.loads(workflow_json)
                    nodes = workflow_data.get('nodes', [])
                    first_node = next((n for n in nodes if n['id'] == '0' and n['type'] == 'form'), None)
                    if first_node:
                        node_service.handle_form_node(workflow, first_node, 0)

                # Notify workflow users
                # request.env['workflow.notification'].sudo().send_to_users(
                #     workflow.id,
                #     {"type": "update_workflow_details", "workflow_id": workflow.hash_key},
                #     request.env.user.email
                # )

                # Log audit event
                # user_ip = request.env['res.users'].sudo().get_user_ip(request.httprequest)
                # request.env['workflow.audit.log'].sudo().create({
                #     'user_id': request.env.user.id,
                #     'message': f"You updated workflow <b>{name}</b> from IP: <b>{user_ip}</b>",
                #     'event_type': 'workflow',
                # })

                return {
                    "success": True,
                    "message": "Workflow detail has been updated!",
                    "data": workflow.read()[0],
                }

            except Exception as e:
                _logger.error(f"Error updating workflow: {str(e)}")
                return {"success": False, "message": "Error updating workflow data."}

        except Exception as e:
            _logger.error(f"Error in update_workflow: {str(e)}")
            return {"success": False, "message": f"An error occurred: {str(e)}"}
