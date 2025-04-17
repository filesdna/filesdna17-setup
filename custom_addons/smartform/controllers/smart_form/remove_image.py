import json
import os
from odoo.http import request, Response
from odoo.addons.smartform.services.google_storage import LocalStorageService
from odoo.tools import config
from odoo import http
import logging

_logger = logging.getLogger(__name__)

server_path = config['server_path']


class ImageRemovalController(http.Controller):

    @http.route('/remove/image', type='http', auth='none', methods=['POST'], csrf=False)
    def remove_image(self, **kwargs):
        try:
            image_url = kwargs.get('image')
            if not image_url:
                return Response(
                    json.dumps({'message': 'No param - image name', 'success': False}),
                    status=400,
                    mimetype='application/json'
                )
            
            # Extract file name and delete from local storage and bucket
            image_name = image_url.split('/')[-1]
            temp_path = f"{server_path}/smartform/static/src/images"
            local_image_path = os.path.join(temp_path, image_name)

            # Remove locally
            if os.path.exists(local_image_path):
                os.remove(local_image_path)
            
            # Remove from Google Cloud Storage
            db_name = request._cr.dbname
            destination_path = f"{db_name}/smartform/images/{image_name}"

            gcs_service = LocalStorageService()
            gcs_service.delete_file(destination_path)

            return Response(
                json.dumps({'message': 'Removed image', 'success': True}),
                status=200,
                mimetype='application/json'
            )

        except Exception as e:
            _logger.error(f"Error removing image: {str(e)}")
            return Response(
                json.dumps({'message': f"Error: {str(e)}", 'success': False}),
                status=500,
                mimetype='application/json'
            )
