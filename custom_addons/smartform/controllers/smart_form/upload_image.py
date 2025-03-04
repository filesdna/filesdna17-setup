import os
import logging
import json
from odoo import http
from odoo.http import request, Response
from werkzeug.utils import secure_filename
from datetime import datetime
from odoo.tools import config
from odoo.addons.smartform.services.google_storage import LocalStorageService

_logger = logging.getLogger(__name__)

server_path = config['server_path']

class UploadImageController(http.Controller):
    
    @http.route('/upload/image', type='http', auth='none', methods=['POST'], csrf=False)
    def upload_image(self, **kwargs):
        try:
            user_id = kwargs.get('user')
            old_image = kwargs.get('old')
            user = None
            if user_id:
                user = request.env['res.users'].sudo().search([('id', '=', int(user_id))], limit=1)
                
            allowed_dir = f"{server_path}/smartform/static/src/images"
            os.makedirs(allowed_dir, exist_ok=True)  # Ensure the directory exists
            
            uploaded_file = request.httprequest.files.get('image')
            _logger.info(f"image::: {uploaded_file}")
            
            if old_image:
                old_image_path = os.path.join(allowed_dir, os.path.basename(old_image))
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            
            if uploaded_file:
                extension = secure_filename(uploaded_file.filename).split('.')[-1]
                timestamp = int(datetime.now().timestamp() * 1000)
                file_name = f"{timestamp}.{extension}"
                image_path = os.path.join(allowed_dir, file_name)
                
                _logger.info(f"Saving file to: {image_path}")
                
                try:
                    # Manually write the file contents
                    with open(image_path, 'wb') as f:
                        f.write(uploaded_file.read())
                    _logger.info(f"File saved successfully at {image_path}")
                except Exception as e:
                    _logger.error(f"Error saving file: {e}")
                    return Response(
                        json.dumps({'message': f"Error saving file: {e}", 'success': False}),
                        status=500,
                        mimetype='application/json'
                    )

                # Prepare Google Cloud Storage options
                db_name = request.env['ir.config_parameter'].sudo().get_param('web.base.url').split("//")[1].split(".")[0]
                destination_path = f"{db_name}/smartform/images/{file_name}"
                gcs_service = LocalStorageService()

                # Upload the file to Google Cloud Storage without encryption key
                upload_response = gcs_service.upload_file(image_path, destination_path, encryption_key=None)

                if not upload_response['success']:
                    _logger.error(f"Upload to Google Cloud failed: {upload_response['message']}")
                    return Response(
                        json.dumps({'message': upload_response['message'], 'success': False}),
                        status=500,
                        mimetype='application/json'
                    )

                if os.path.exists(image_path):
                    os.remove(image_path)
                    _logger.info(f"Local file {image_path} deleted after upload.")

                image_url = f"{request.env['ir.config_parameter'].sudo().get_param('web.base.url')}/get/image/{db_name}/{timestamp}/{extension}"
                return Response(
                    json.dumps({'image': image_url, 'success': True}),
                    status=200,
                    mimetype='application/json'
                )

            return Response(
                json.dumps({'message': 'No image uploaded', 'success': False}),
                status=400,
                mimetype='application/json'
            )
            
        except Exception as e:
            _logger.error(f"Error uploading image: {str(e)}")
            return Response(
                json.dumps({'message': f"Error: {str(e)}", 'success': False}),
                status=500,
                mimetype='application/json'
            )
