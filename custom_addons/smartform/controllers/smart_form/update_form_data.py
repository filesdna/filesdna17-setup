import os
import json
import logging
from odoo import http
from odoo.http import request, Response
from odoo.tools import config
from odoo.addons.smartform.services.google_storage import LocalStorageService

_logger = logging.getLogger(__name__)

server_path = config['server_path']

class SmartFormUpdateFormController(http.Controller):

    @http.route('/smartform/update-form-data', type='http', auth='public', methods=['POST'], csrf=False)
    def update_form_data(self, **kwargs):
        try:
            # Extract inputss
            form_hash = kwargs.get('hash')
            form_data = kwargs.get('form_data')

            if not form_hash or not form_data:
                return Response(
                    json.dumps({'message': "Both 'hash' and 'form_data' are required.", 'success': False}),
                    status=400,
                    mimetype='application/json'
                )

            # Fetch the form record using the hash
            form = request.env['smart.form'].sudo().search([('hash', '=', form_hash)], limit=1)
            if not form:
                return Response(
                    json.dumps({'message': f"No form with hash {form_hash}.", 'success': False}),
                    status=404,
                    mimetype='application/json'
                )

            # Generate the temporary path
            temp_path = f"/tmp/{form.form_data}"

            # Write the form data to the temporary file
            with open(temp_path, 'w') as temp_file:
                json.dump(json.loads(form_data), temp_file)

            # Fetch the encryption key and user information
            encryption_key = request.env.user.company_id.encription_key

            # Prepare upload options
            db_name = request.env['ir.config_parameter'].sudo().get_param('web.base.url').split("//")[1].split(".")[0]
            destination_path = f"{db_name}/smartform/forms/{form.form_data}"

            gcs_service = LocalStorageService()

            # Upload the JSON file to Google Cloud Storage with encryption
            gcs_service.upload_file(temp_path, destination_path, encryption_key)

            # Log success and clean up the temporary file
            _logger.info(f"Form data uploaded successfully to {destination_path}.")
            if os.path.exists(temp_path):
                os.remove(temp_path)

            return Response(
                json.dumps({'message': "Form data updated!", 'success': True}),
                status=200,
                mimetype='application/json'
            )

        except Exception as e:
            _logger.error(f"Error updating form data: {str(e)}")
            return Response(
                json.dumps({'message': f"Error: {str(e)}", 'success': False}),
                status=500,
                mimetype='application/json'
            )
