import os
import json
import logging
from odoo import http
from odoo.http import request, Response
from odoo.tools import config

_logger = logging.getLogger(__name__)

server_path = config['server_path']

class TemplateController(http.Controller):

    @http.route('/smartform/templates/<string:title>', type='http', auth='public', methods=['GET'], csrf=False)
    def get_template(self,title, **kwargs):
        try:
            if not title:
                response_data = {
                    'message': 'no param - template title',
                    'success': False
                }
                return Response(json.dumps(response_data), status=400, mimetype='application/json')

            # Construct the file path
            templates_path = f'{server_path}/smartform/static/src/assets/forms/templates'  # Update this path as needed
            file_path = os.path.join(templates_path, f"{title}.json")

            # Check if the file exists and return it, or respond with an error
            if os.path.exists(file_path):
                return http.send_file(file_path)
            else:
                response_data = {
                    'message': 'no template',
                    'success': False
                }
                return Response(json.dumps(response_data), status=404, mimetype='application/json')

        except Exception as e:
            _logger.error(f"Error retrieving template: {str(e)}")
            response_data = {
                'message': f"Error: {str(e)}",
                'success': False
            }
            return Response(json.dumps(response_data), status=500, mimetype='application/json')
