from datetime import datetime
from odoo.tools import config
from odoo.addons.workflow.services.google_storage import LocalStorageService
from odoo.addons.workflow.services.helpers import WorkflowHelper
from odoo.addons.workflow.services.email_template import mail_data
from odoo.http import request
import logging
import json
import os
import random
import string

_logger = logging.getLogger(__name__)

server_path = config['server_path']

workflow_helper = WorkflowHelper()

class FormNode:
    def handle_form_node(self, workflow, node, sub_id):
        """
        Process a form node in the workflow.

        :param workflow: Workflow record
        :param node: Current node in the workflow (dictionary)
        :param sub_id: Submission ID
        """
        try:
            form = self._get_form(node["data"]["form"])  # Access `node` as a dictionary
            
            # Create workflow form entry
            workflow_form_vals = {
                "workflow_id": workflow.id,
                "form_id": form.id,
                "assign_email": "" if node["id"] == "0" else node["data"].get("email", ""),
                "node_id": node["id"],
                "status": "pending",
                "submission_id": sub_id,
            }
            request.env['workflow.forms'].sudo().create(workflow_form_vals)
            
            # If the form is a template
            if "template-" in str(node['data']['form']):
                self._handle_template_form(workflow, node, sub_id, form)
                return
            
            # If the node id == 0, exit
            if node["id"] == "0":
                return
            
            invite_data = {
                "form": form.hash,
                "from_user": f"Workflow:{workflow.id}",
                "to_user": node["data"]["email"],
            }

            # Check if an invitation already exists
            count = request.env["invite"].sudo().search_count(
                [
                    ("form", "=", invite_data["form"]),
                    ("from_user", "=", invite_data["from_user"]),
                    ("to_user", "=", invite_data["to_user"]),
                    ("done", "=", '0'),
                ]
            )

            # Create the invitation if it does not exist
            if not count:
                request.env["invite"].sudo().create(
                    {
                        **invite_data,
                        "message": "Workflow invitation email to fill form",
                    }
                )

            # Send invitation email for form filling
            mail_data(
                email_type="workflow_assign",
                subject=f"You received an invitation to fill form from Workflow - '{workflow.name}'",
                email_to=node["data"]["email"],
                header=f"Hello {node['data']['email']},",
                description=f"You are assigned to fill form for Workflow - '{workflow.name}'.",
                base_url=f"{request.env['ir.config_parameter'].sudo().get_param('web.base.url')}/publicform/{form.hash}?from={node['data']['email']}"
            )

            # Add activity log
            data = {
                "type": "form-assign",
                "message": f"Workflow assigned a form '{form.name}' (#{form.id}) to {node['data']['email']}.",
                "workflow_id": workflow.id,
                "node_id": node["id"],
                "submission_id": sub_id,
            }

            workflow_helper.add_activity_log(data)

        except Exception as e:
            _logger.error(f"Error in handle_form_node: {str(e)}")
            raise

    def _get_form(self, form_data):
        """
        Retrieve form based on form_data.

        :param form_data: Form data (ID or template string)
        :return: Form record
        """
        if "template-" in str(form_data):
            template_id = int(form_data.replace("template-", ""))
            return request.env['dms.file'].sudo().search([('id', '=', template_id)], limit=1)
        else:
            return request.env['smart.form'].sudo().search([('id', '=', form_data)], limit=1)

    def _handle_template_form(self, workflow, node, sub_id, form):
        """
        Handle template-specific logic in the workflow.

        :param workflow: Workflow record
        :param node: Current node
        :param sub_id: Submission ID
        :param form: Template form record
        """
        try:
            # Ensure 'data' exists in the node
            node_data = node.get('data', {})
            if not node_data:
                raise ValueError("Node data is missing or invalid")

            # Generate document name
            file_name = node_data.get('file_name', 'default_file_name')
            doc_name = f"{file_name}-{datetime.now().timestamp()}"

            # Validate required fields
            template_form = node_data.get('form')
            if not template_form or "template-" not in template_form:
                raise ValueError("Template form is invalid or missing")

            # Retrieve template data
            append_json = form.append_json if hasattr(form, 'append_json') else None
            api_ary = self._get_append_data(append_json) if append_json else []

            # Handle nested workflows
            nested_workflows = node_data.get("workflow", [])
            resolved_workflows = []
            for wf in nested_workflows:
                form_ids = wf.get("formId")
                _logger.info(f"test1:{form_ids}")
                if isinstance(form_ids, list):
                    _logger.info(f"test1:{form_ids}")
                    # Process an array of form IDs
                    form_data_array = [
                        self._process_form_id(form_id, workflow, sub_id)
                        for form_id in form_ids
                    ]
                    
                    wf["data"] = form_data_array
                else:
                    _logger.info(f"test1:{form_ids}")
                    # Process a single form ID
                    form_data = self._process_form_id(form_ids, workflow, sub_id)
                    wf.update(form_data)

                resolved_workflows.append(wf)

            # Combine resolved workflows with append data
            if append_json:
                api_ary = self._get_append_data(append_json)
            api_ary = [d for d in api_ary if d.get("type") != "workflow"]
            api_ary.extend(resolved_workflows)

            # Assign roles and handle documents
            
            document_id = self._assign_roles_and_process_documents(node, api_ary, doc_name, workflow, sub_id, form)
                
            # Call the workflow controller to handle the template workflow
            
            if document_id:
                # Prepare inputs for the workflow template
                temp_inputs = {
                    "params": {
                        "workflow_id": workflow.id,
                        "template_id": int(template_form.replace("template-", "")),
                        "node_id": node.get('id', ''),
                        "submission_id": sub_id,
                        "document_id": str(document_id),
                        "roles": json.dumps(node_data.get('roles', {})),
                        "status": node_data.get('action', 'pending'),
                        "is_completed": node_data.get('is_completed', False),
                    }
                }
                workflow_helper.call_controller("workflow/add-template-workflow", temp_inputs)


        except Exception as e:
            _logger.error(f"Error in _handle_template_form: {str(e)}")
            raise



    def _assign_roles_and_process_documents(self, node, api_ary, doc_name, workflow, sub_id, form):
        try:
            assign_roles = self._process_roles(node, api_ary)
            inputs = {
                "params": {
                    "assign_roles": assign_roles,
                    "template_id": int(node['data']['form'].replace("template-", "")),
                    "name": doc_name,
                    "apiAry": api_ary,
                    "folder_id": int(node['data'].get('folder_id', 1)[0]),
                    "type": "sign",
                    "is_last_completed": node['data'].get('is_completed', True),
                }
            }
            
            # create the document from the template
            response = workflow_helper.call_controller("template/use", inputs)
            
            # # update the workflow template
            # workflow_template = request.env['workflow.templates'].sudo().search([('submission_id','=',int(sub_id)),('node_id','=',str(node["id"]))])
            # _logger.info(f"node[id]:{str(node['id'])}")
            # _logger.info(f"sub_id:{sub_id}")
            # _logger.info(f"workflow_template:{workflow_template}")

            # if response['result']['docData']['id']:
            #     _logger.info(f"response.docData['id']:{response['result']['docData']['id']}")
            #     workflow_template.write({ "document_id": str(response['result']['docData']['id']) })
            return response['result']['docData']['id']
        except Exception as e:
            _logger.error(f"Error assing_roles_and_process_documents: {str(e)}")


    def _get_append_data(self, route):
        """Retrieve append data."""
        try:
            # Define path for JSON retrieval based on the environment setup
            _temp = f"{server_path}/dms_editor/static/src/temp"
            json_filepath = os.path.join(_temp, route)
            if os.path.exists(json_filepath):
                os.remove(json_filepath)
            key = request.env.user.company_id.encription_key
            db_name = request._cr.dbname
            destination_path = f"{db_name}/append_jsons/{route}"
            gcs_service = LocalStorageService()
            gcs_service.download_file(destination_path, json_filepath, encryption_key=key)
            with open(json_filepath, 'r', encoding='utf-8') as file:
                content = file.read()
                return json.loads(content)
        except Exception as e:
            _logger.error(f"Error retrieving append data: {str(e)}")
            return []


    def _process_form_id(self, form_id, workflow, sub_id):
        """
        Process a single form ID.
        """
        try:
            if not str(form_id).startswith('template'):
                _logger.info(f"test1:{form_id}")
                # Handle non-template forms
                form = request.env['smart.form'].sudo().search([('id', '=', form_id)], limit=1)
                if not form:
                    raise ValueError(f"Form with id {form_id} not found")

                submission = request.env['submission'].sudo().search([
                    ('id', '=', sub_id),
                    ('form_id', '=', form.hash)
                ], limit=1)
                if not submission:
                    raise ValueError(f"Submission with id {sub_id} and form_id {form.hash} not found")

                approver = request.env['workflow.approves'].sudo().search([
                    ('workflow_id', '=', workflow.id),
                    ('submission_id', '=', sub_id),
                    ('form_id', '=', form_id)
                ], limit=1)
                approver_data = {
                    "id": approver.id,
                    "workflow_id": approver.workflow_id.id if approver.workflow_id else None,
                    "form_id": approver.form_id,
                    "node_id": approver.node_id,
                    "type": approver.type,
                    "status": approver.status,
                    "outcomes": approver.outcomes,
                    "approver": approver.approver,
                    "rule": approver.rule,
                    "notify": approver.notify,
                    "require_login": approver.require_login,
                    "signature": approver.signature,
                    "comment": approver.comment,
                    "reassign": approver.reassign,
                    "require_comment": approver.require_comment,
                    "escalate": approver.escalate,
                    "escalate_date": approver.escalate_date.strftime("%Y-%m-%d") if approver.escalate_date else None,
                    "escalate_email": approver.escalate_email,
                    "auto_finish": approver.auto_finish,
                    "auto_finish_date": approver.auto_finish_date.strftime("%Y-%m-%d") if approver.auto_finish_date else None,
                    "auto_finish_outcome": approver.auto_finish_outcome,
                    "submission_id": approver.submission_id
                }
                return {
                    "form": {
                        "name": form.name,
                        "data": json.loads(submission.data),
                        "approve_data": approver_data,
                    }
                }
            else:
                _logger.info(f"process1:")
                # Handle template forms
                template_id = int(str(form_id).replace('template-', ''))
                _logger.info(f"process2:{template_id}")
                template_data = request.env['workflow.templates'].sudo().search([
                    ('workflow_id', '=', workflow.id),
                    ('submission_id', '=', sub_id),
                    ('template_id', '=', template_id)
                ], limit=1)
                _logger.info(f"process3:{template_data}")
                if template_data:
                    hash_key = ''.join(random.choices(string.ascii_letters + string.digits, k=15))
                    request.env['document.load.image'].sudo().create({
                        'doc_image_id': template_data.document_id,
                        'hash_key': hash_key,
                        'image_type': 'F',
                    })

                    document_name = request.env['dms.file'].sudo().search([
                        ('id', '=', template_data.document_id)
                    ], limit=1)
                    _logger.info(f"process4:{document_name}")
                    return {
                        "document": {
                            "name": document_name.name,
                            "link": f"{request.env['ir.config_parameter'].sudo().get_param('web.base.url')}/api/get-detail-view/{hash_key}"
                        }
                    }
        except Exception as e:
            _logger.error(f"Error process_form_id: {str(e)}")


    def _append_user_to_role(self, roles, api_ary):
        """
        Append users to roles by matching role IDs in `api_ary`.

        :param roles: List of role dictionaries with user assignments.
        :param api_ary: List of API data containing role details.
        """
        try:
            for role in roles:
                for item in api_ary:
                    item_role = item.get("role")
                    if item_role and item_role.get("id") == role.get("id"):
                        if not item_role.get("user"):
                            item_role["user"] = role.get("user")
        except Exception as e:
            _logger.error(f"Error append user to role: {str(e)}")


    def _process_roles(self, node, api_ary):
        """
        Process roles and assign users with the appropriate attributes.

        :param node: Node data containing roles and enableOrder flag.
        :param api_ary: List of API data.
        :return: Dictionary of processed roles.
        """
        try:
            self._append_user_to_role(node["data"]["roles"], api_ary)

            # Map roles to their corresponding user assignments
            assigned_roles = [role["user"] for role in node["data"]["roles"]]
            result = {}

            for obj in assigned_roles:
                key = list(obj.keys())[0]
                data = obj[key]
                result[key] = {
                    **data,
                    **({} if node["data"].get("enableOrder") else {"order_by": 0}),
                }

            return result
        except Exception as e:
            _logger.error(f"Error process roles: {str(e)}")