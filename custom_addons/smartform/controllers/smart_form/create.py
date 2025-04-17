import hashlib
import os
import json
from datetime import datetime
from odoo import http
from odoo.http import request, Response
from odoo.tools import config
from odoo.addons.smartform.services.helpers import serialize_record
from odoo.addons.smartform.services.google_storage import LocalStorageService
import logging

_logger = logging.getLogger(__name__)

 
server_path = config['server_path']

class SmartFormCreateController(http.Controller):

    @http.route('/smartform/create', type='http', auth='public', methods=['POST'], csrf=False)
    def create_smartform(self, **kwargs):
        try:
            name = kwargs.get('name')
            form_type = kwargs.get('type')
            folder_id = kwargs.get('folder_id')
            user_id = kwargs.get('user_id')
            form_data = kwargs.get('form_data', '')
            template = kwargs.get('template')
            _logger.info(f"Form Data1: {form_data}")
            
            # Check if a smart form with the same name exists
            existing_count = request.env['smart.form'].sudo().search_count([
                ('user_id', '=', user_id),
                ('name', '=', name)
            ])

            if existing_count:
                if template:
                    name = f"{name} - {int(datetime.now().timestamp())}"
                else:
                    return Response(
                        json.dumps({'message': "This name was already used.", 'success': False}),
                        status=400,
                        content_type='application/json'
                    )

            # Check if the template file exists
            template_path = f'{server_path}/smartform/static/src/assets/forms/templates/{template}.json'
            if template and not os.path.exists(template_path):
                return Response(
                    json.dumps({'message': "This template is not available.", 'success': False}),
                    status=400,
                    content_type='application/json'
                )

            # Create the smart form record
            smart_form = request.env['smart.form'].sudo().create({
                'name': name,
                'type': form_type,
                'folder_id': folder_id,
                'user_id': user_id,
                'team_id': user_id,
                'form_data': form_data
            })

            # Generate hash and handle template logic
            if smart_form:
                if form_type == 'folder':
                    return Response(
                        json.dumps({'message': "Folder was created.", 'success': True, 'data': serialize_record(smart_form.read()[0])}),
                        content_type='application/json'
                    )

                # Generate hash
                hash_value = hashlib.sha1(f"{user_id}{smart_form.id}".encode()).hexdigest()

                # Use the appropriate template path or fallback to temp.json
                temp_path = template_path if template else f'{server_path}/smartform/static/src/assets/forms/temp.json'

                file_name = f"{name}.json"
                encryption_key = request.env.user.company_id.encription_key

                # Prepare upload details
                db_name = request._cr.dbname
                destination = f"{db_name}/smartform/forms/{file_name}"

                # Initialize Google Cloud Storage service
                gcs_service = LocalStorageService()
                upload_response = gcs_service.upload_file(temp_path, destination, encryption_key)

                if not upload_response.get('success'):
                    raise ValueError(upload_response.get('message'))

                # Update the smart form with hash and form data
                smart_form.write({'hash': hash_value, 'form_data': file_name})

                # Convert any datetime fields to strings
                form_data = smart_form.read()[0]
                serialized_data = serialize_record(smart_form.read()[0])

                return Response(
                    json.dumps({'message': "Form created!", 'data': serialized_data, 'success': True}),
                    content_type='application/json'
                )
            else:
                return Response(
                    json.dumps({'message': "Error creating form!", 'success': False}),
                    status=500,
                    content_type='application/json'
                )
        except Exception as e:
            _logger.error(f"Error creating form: {str(e)}")
            return Response(
                json.dumps({'message': f"Error: {str(e)}", 'success': False}),
                status=500,
                content_type='application/json'
            )
