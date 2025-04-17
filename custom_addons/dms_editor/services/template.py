import json
from datetime import datetime
from odoo import http
from odoo.http import request
from odoo.tools import config
from odoo.addons.dms_editor.services.files import Files
from odoo.addons.dms_editor.services.qr_code import generate_branded_qr
import logging
from odoo.addons.dms_editor.services.email_template import create_log_note

_logger = logging.getLogger(__name__)

server_path = config['server_path']

file_service = Files()

class TemplateService:
    def template_copy_pdf(self, template_id, name, user_details, assign_roles, api_ary, folder_id=1, is_myself=False):
        """
        Copy a template PDF and process it with modifications.

        :param name: Name of the document.
        :param template_id: Template ID.
        :param user_details: Dictionary containing user details.
        :param assign_roles: JSON containing assigned roles.
        :param api_ary: JSON containing API data.
        :param folder_id: Folder ID (optional).
        :param is_myself: Boolean indicating if the user is processing their own document.
        :return: Dictionary with document ID and JSON data.
        """
        document = False
        json_data = None
        try:
            first_name = user_details.name
            email = user_details.email

            # Fetch the template document
            template_document = request.env['dms.file'].sudo().search([('id', '=', template_id)], limit=1)
            if not template_document:
                _logger.error("Template document not found.")
                return {"id": document_id, "json_data": None}

            location = f"{server_path}/dms_editor/static/src"
            current_time = int(datetime.now().timestamp())
            full_name = f"{name}-{current_time}.json" 
            db_name= request.env['ir.config_parameter'].sudo().get_param('web.base.url').split("//")[-1].split(".")[0]
            google_bucket_destination = f"{db_name}/append_jsons/{full_name}"

            local_path_destination_json = f"{location}/temp/{full_name}"

            try:
                qr_code = generate_branded_qr()

                # Create the document in the database
                document = self.create_document_record(
                    name, template_document, folder_id, user_details, current_time, full_name
                )

                json_data = self.process_json_data(
                    api_ary, assign_roles, is_myself, first_name, email, qr_code, document.barcode_url
                )

                with open(local_path_destination_json, 'w', encoding='utf-8') as json_file:
                    json.dump(json_data, json_file)

                # Upload JSON to bucket
                file_service.upload_to_gcs(local_path_destination_json, google_bucket_destination)

            except Exception as e:
                _logger.error(f"Error processing template: {str(e)}")
                return False

            create_log_note(template_id, f"{first_name} has created a new document with name {name}")
            # Cleanup temporary files
            file_service._delete_temp_files([local_path_destination_json])
            return {"id": document.id, "json_data": json_data}

        except Exception as e:
            _logger.error(f"Error in template_copy_pdf: {str(e)}")
            return False



    def process_json_data(self, api_ary, assign_roles, is_myself, name, email, qr_code, barcode):
        try:
            for element in api_ary:
                # Safely access the role key
                role = element.get('role')
                if role and isinstance(role, dict) and role.get('id'):
                    # Assign signer if the role has an ID
                    element['signer'] = {
                        "first_name": name,
                        "last_name": "",
                        "email": email
                    } if is_myself else assign_roles.get(str(role['id']))

                # Add QR code data
                if element['type'] == 'qr':
                    element['data'] = qr_code

                # Add barcode data
                if element['type'] == 'barcode':
                    element['data'] = barcode

                # Generate a reference number
                if element['type'] == 'refnumber':
                    prefix = element.get('data', '')
                    ref_number = f"{prefix}-{datetime.now().microsecond}"  # Mocked reference number logic
                    element['data'] = ref_number

            return api_ary
        except Exception as e:
            _logger.error(f"Error in processing data: {str(e)}")
            return False

    def create_document_record(self, name, template_document, folder_id, user, current_time, append_json):
        try:
            directory_storage = request.env['dms.directory'].sudo().search([('id','=',int(folder_id))]).storage_id.id
            file = request.env['dms.file'].sudo().create({
                "name" : f"{name}.pdf",
                'directory_id': int(folder_id),
                'content' : template_document.content,
                'create_uid' :  user.id,
                'storage_id' : directory_storage,
                'current_time_seconds': current_time,
                'company_id': user.company_id.id,
                "document_status" : "Draft",
                "append_json": append_json,
            })
            _logger.info(f"Creating document record for {name}")
            return file

        except Exception as e:
            _logger.error(f"Error in creating document record: {str(e)}")
            return False
