from datetime import datetime
from odoo.tools import config
from odoo.addons.workflow.services.google_storage import LocalStorageService
from odoo.http import request
import json
import os
import requests
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

server_path = config['server_path']

class WorkflowHelper:
    def delete_workFlow_data(self, workflow_id):
        """Helper function to delete workflow."""
        request.env['workflow.forms'].sudo().search([('workflow_id', '=', workflow_id)]).unlink()
        request.env['workflow.users'].sudo().search([('workflow_id', '=', workflow_id)]).unlink()
        request.env['workflow.emails'].sudo().search([('workflow_id', '=', workflow_id)]).unlink()
        request.env['workflow.approves'].sudo().search([('workflow_id', '=', workflow_id)]).unlink()
        request.env['workflow.templates'].sudo().search([('workflow_id', '=', workflow_id)]).unlink()
        request.env['workflow.activity'].sudo().search([('workflow_id', '=', workflow_id)]).unlink()
        request.env['invite'].sudo().search([('from_user', '=', f"Workflow:{workflow_id}")]).unlink()
        request.env['workflow'].sudo().search([('id', '=', workflow_id)]).unlink()
        return True


    def add_activity_log(self, data):
        add_log = request.env['workflow.activity'].sudo().create({
        "type": data['type'],  # Access dictionary keys
        "workflow_id": data['workflow_id'],
        "message": data['message'],
        "node_id": data.get('node_id'),  # Use .get() for optional keys
        "submission_id": data.get('submission_id'),
        })
        return add_log

    def get_workflow_json(self,user_id, json_file):
        try:
            user = request.env['res.users'].sudo().browse(int(user_id))
            if not user:
                raise UserError("User not found.")
            temp_dir = f"{server_path}/dms_editor/static/src/temp"
            os.makedirs(temp_dir, exist_ok=True)
            local_path = os.path.join(temp_dir, f"{json_file}.json")
            db_name = request.env['ir.config_parameter'].sudo().get_param('web.base.url').split("//")[1].split(".")[0]
            destination = f"{db_name}/workflow/{json_file}.json"
            encription_key = user.company_id.encription_key
            gcs_service = LocalStorageService()
            gcs_service.download_file(destination, local_path, encryption_key=encription_key)
            # Read and parse the JSON file
            with open(local_path, "r", encoding="utf-8") as file:
                workflow_data = json.load(file)

            # Clean up the temporary file
            os.remove(local_path)
            return workflow_data
        except Exception as e:
            raise UserError(f"Error fetching workflow JSON: {str(e)}")

    def get_next_nodes(self, workflow, node_id):
        """
        Get the next nodes in the workflow based on edges and nodes.

        :param workflow: Workflow record containing user_id and workflow_json.
        :param node_id: Current node ID.
        :return: List of next nodes.
        """
        try:
            # Load workflow JSON
            workflow_json = self.get_workflow_json(workflow.user_id, workflow.workflow_json)

            nodes = workflow_json.get('nodes', [])
            edges = workflow_json.get('edges', [])

            # Filter edges and nodes for the next steps
            next_edges = [edge for edge in edges if edge.get('source') == node_id]
            next_node_ids = [edge.get('target') for edge in next_edges]
            next_nodes = [node for node in nodes if node.get('id') in next_node_ids]

            return next_nodes

        except Exception as e:
            raise UserError(f"Error getting next nodes: {str(e)}")

    def get_sub_and_form(self, sub_id):
        submission = request.env['submission'].sudo().search([('id', '=', sub_id)], limit=1)
        form = request.env['smart.form'].sudo().search([('hash', '=', submission.form_id)], limit=1)
        return {'submission': submission, 'form': form}



    def generate_dynamic_url(self, model_name, view_type='form'):
        # Fetch the base URL
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')

        # Fetch the menu_id from `ir.ui.menu`
        menu = request.env['ir.ui.menu'].sudo().search([('action', 'like', f"%{model_name}%")], limit=1)
        menu_id = menu.id if menu else None

        # Fetch the action_id from `ir.actions.act_window`
        action = request.env['ir.actions.act_window'].sudo().search([('res_model', '=', model_name)], limit=1)
        action_id = action.id if action else None

        if not menu_id or not action_id:
            return {
                "success": False,
                "message": "Menu or action not found for the given model.",
            }

        return f"{base_url}/web#cids=1&menu_id={menu_id}&action={action_id}&model={model_name}&view_type={view_type}"


    def get_field_value(self, str_value, sub_id):
        """
        Retrieves the value of a specific field from a submission.

        :param str_value: String containing the field identifier (e.g., "field-123").
        :param sub_id: Submission ID.
        :return: Field value or None if not found.
        """
        try:
            # Extract field ID from the string
            field_id = int(str_value.split("-")[1])

            # Retrieve submission and form details
            submission = self.get_sub_and_form(sub_id)
            _logger.info(f"submission: {submission['submission']['data']}")

            # Parse the submission data and find the matching field
            submission_data = json.loads(submission['submission']['data'])
            _logger.info(f"submission_data: {submission_data}")
            field_data = next((f for f in submission_data if f["id"] == field_id), None)

            if not field_data:
                _logger.warning(f"Field with ID {field_id} not found in submission data.")
                return None

            # Get the field value
            field_value = self.get_value(field_data)

            _logger.info(f"get_field_value: {field_value}")

            return field_value
        except Exception as e:
            _logger.error(f"Error in get_field_value: {str(e)}")
            return None

    def get_field_value_placeholder(str_value, sub_id, custom_field_option, submission_model):
        """
        Fetches the value of a specific field in the submission data based on its ID.

        :param str_value: The field identifier string.
        :param sub_id: Submission ID.
        :param custom_field_option: Field option to determine position.
        :param submission_model: The model to query submission data.
        :return: The value at the specified position.
        """
        try:
            # Extract field ID
            field_id = str_value.split("-")[1]
            position = int(custom_field_option[-1])

            # Fetch submission record
            submission = submission_model.sudo().search([("id", "=", sub_id)], limit=1)
            if not submission:
                raise ValueError(f"Submission with ID {sub_id} not found.")

            # Parse submission data
            submission_data = json.loads(submission.data)
            field = next((f for f in submission_data if f["id"] == int(field_id)), None)
            if not field:
                raise ValueError(f"Field with ID {field_id} not found in submission data.")

            # Return value at the specific position
            value = self.get_value(field)
            if isinstance(value, list) and len(value) >= position:
                return value[position - 1]

        except Exception as e:
            _logger.error(f"Error in get_field_value_placeholder: {str(e)}")
            return None

    def call_controller(self, controller, payload):
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        api_url = f"{base_url}/api/{controller}"

        # Add the user's session or token for authentication
        session_cookie = request.httprequest.cookies.get('session_id')
        headers = {
            "Content-Type": "application/json",
            "Cookie": f"session_id={session_cookie}",
        }

        try:
            response = requests.post(api_url, json=payload, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "message": f"HTTP Error {response.status_code}: {response.text}"}
        except Exception as e:
            return {"success": False, "message": f"Error calling API: {str(e)}"}


    def format_date(self, value, date_format="DD/MM/YYYY"):
        """
        Helper function to format a date.
        """
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime(date_format.replace("DD", "%d").replace("MM", "%m").replace("YYYY", "%Y"))
        except ValueError:
            return ""

    def format_time(self, value, time_format="HH:mm"):
        """
        Helper function to format a time.
        """
        try:
            return datetime.strptime(value, "%H:%M:%S").strftime(time_format.replace("HH", "%H").replace("mm", "%M"))
        except ValueError:
            return ""

    def get_value(self, el: dict):
        """
        Extracts and formats the value based on the type of element.

        :param el: Dictionary containing type and value of the element.
        :return: Formatted value based on the type.
        """
        el_type = el.get("type")
        value = el.get("value")

        if el_type == "appointment":
            return f"{self.format_date(value[0], el.get('dateFormat', 'DD/MM/YYYY')) if value and value[0] else ''} {value[1] if value and len(value) > 1 else ''}"

        if el_type == "datePicker":
            return f"{self.format_date(value[0], el.get('format', 'DD/MM/YYYY')) if value and value[0] else ''} {self.format_time(value[1], el.get('timeFormat', 'HH:mm')) if value and len(value) > 1 else ''}"

        if el_type == "time":
            if isinstance(value, list) and len(value) == 2:
                return f"{self.format_time(value[0], el.get('timeFormat', 'HH:mm'))} - {self.format_time(value[1], el.get('timeFormat', 'HH:mm'))}"
            elif value:
                return self.format_time(value, el.get("timeFormat", "HH:mm"))

        if el_type in ["fullname", "phone"]:
            return " ".join(value) if isinstance(value, list) else value

        if el_type == "address":
            return ", ".join(value) if isinstance(value, list) else value

        if el_type == "multipleChoice":
            return sorted(value) if isinstance(value, list) else value

        return value