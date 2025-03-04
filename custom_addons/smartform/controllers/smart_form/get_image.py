import os
import logging
import json
from odoo import http
from datetime import datetime
from odoo.tools import config
from odoo.addons.smartform.services.google_storage import LocalStorageService
from odoo.http import request

_logger = logging.getLogger(__name__)

server_path = config['server_path']

class ImageRetrievalController(http.Controller):

    @http.route('/get/image/<string:company>/<string:image>/<string:extension>', type='http', auth='none', methods=['GET'],csrf=False)
    def get_image(self, company, image, extension, **kwargs):
        try:
            temp_path = f"{server_path}/smartform/static/src/images"
            file_name = f"{image}.{extension}"
            local_image_path = os.path.join(temp_path, file_name)
            db_name = request.env['ir.config_parameter'].sudo().get_param('web.base.url').split("//")[1].split(".")[0]
            # Download from Google Cloud Storage if not present locally
            if not os.path.exists(local_image_path):
                # Upload to Google Cloud Storage (adjust your service accordingly)
                # Prepare upload options
                destination_path = f"{db_name}/smartform/images/{file_name}"

                gcs_service = LocalStorageService()
                gcs_service.download_file( destination_path, local_image_path, encryption_key=None)

            # Serve the file if exists or serve a placeholder
            if os.path.exists(local_image_path):
                return http.send_file(local_image_path)
            else:
                placeholder_path = os.path.join(temp_path, 'no-image.png')
                return http.send_file(placeholder_path)

        except Exception as e:
            _logger.error(f"Error retrieving image: {str(e)}")
            placeholder_path = os.path.join(temp_path, 'no-image.png')
            return http.send_file(placeholder_path)
