import logging
import os
import json
import hashlib
import base64
import requests
from odoo import http
from datetime import datetime
from odoo.http import request, Response
from odoo.tools import config
from odoo.addons.dms_editor.services.google_storage import LocalStorageService
from odoo.addons.dms_editor.services.signature import SignatureHelper

_logger = logging.getLogger(__name__)
 
server_path = config['server_path']

class SignatureController(http.Controller):

    @http.route('/api/add-sign', type='http', auth='none', methods=['POST'], csrf=False)
    def get_signature_base64(self, **kwargs):
        try:
            params = kwargs
            signatur = ""
            signature_type = params.get('type')
            p_type = params.get('pType')
            sign_id = params.get('sign_id')
            user_doc_owner = params.get('user_id')

            signature = SignatureHelper()

            # Fetch signature based on `sign_id`
            get_dsign = None
            get_user = None

            if sign_id:
                get_dsign = request.env['user.signature'].sudo().search([('id', '=', int(sign_id))], limit=1)
                _logger.info(f"get_dsign:{get_dsign}")
                if get_dsign:
                    get_user = request.env['dms.file'].sudo().search([('create_uid', '=', get_dsign.user_id.id)], limit=1)
                    gcs = LocalStorageService()
                    if p_type == "initial":
                        base64_data = gcs.read_url(get_dsign.initial_signature.split(f"{google_bucket}/"))
                        return Response(
                            json.dumps({'success': True, 'data': base64_data}),
                            status=200,
                            mimetype='application/json'
                        )

                    if p_type == "full":
                        url = gcs.read_url(get_dsign.full_signature.split(f"{google_bucket}/")[1])
                        base64_data = self.url_to_base64(url)
                        return Response(
                            json.dumps({'success': True, 'data': base64_data}),
                            status=200,
                            mimetype='application/json'
                        )
                else:
                    return Response(
                        json.dumps({'success': False}),
                        status=404,
                        mimetype='application/json'
                    )

            # Use Puppeteer-like functionality (emulated or a placeholder) to generate a signature
            if signature_type == "choose":
                user_owner = request.env['res.users'].sudo().search([('id', '=', user_doc_owner)], limit=1)

                user_name = params.get('full_name')
                if not get_dsign:
                    get_dsign = {}
                    get_user = {}

                if p_type == "initial":
                    user_name = params.get('initial_name')

                signature_font = f"sign{params.get('signature_font')}" if params.get('signature_font') != "roboto" else "roboto"
                signatur = signature.upload_signature(
                    name=user_name,
                    font_path=f"{server_path}/dms_editor/static/src/fonts/{signature_font}.ttf",
                    sign_type=p_type,
                    sign_by=params.get('sign_by', user_name),
                    date=params.get('date', ""),
                    reason=params.get('reason', ""),
                    no_design=params.get('no_design', 0),
                    base64_output=True
                )
            elif signature_type in ["draw", "upload"]:
                user_name = params.get('full_name')
                base64_data = params.get('signature')
                if p_type == "initial":
                    base64_data = params.get('initial')
                    user_name = params.get('initial_name')

                hash_key = self.calculate_file_hash(user_name, "base64")
                if p_type == "initial":
                    hash_key = ""

                signatur = signature.generate_html_signature_base64(
                    base64_data,
                    hash_key,
                    p_type,
                    user_name if params.get('sign_by', user_name) else params.get('sign_by', user_name),
                    params.get('date', ""),
                    params.get('reason', ""),
                    params.get('no_design', 0)
                )

            # Return the generated signature
            return Response(
                json.dumps({'success': True, 'data': signatur}),
                status=200,
                mimetype='application/json'
            )

        except Exception as e:
            _logger.error(f"Error generating signature: {str(e)}")
            return Response(
                json.dumps({'success': False, 'message': "An error occurred while processing your request."}),
                status=500,
                mimetype='application/json'
            )

    def calculate_file_hash(self, data, encoding):
        """ Placeholder for calculating file hash """
        # Simulate hash calculation
        return hashlib.sha512(data.encode()).hexdigest()


    def url_to_base64(self, url):
        try:
            # Fetch the file from the URL
            response = requests.get(url)
            _logger.info(f"HTTP Status: {response.status_code}")
            _logger.info(f"Content-Type: {response.headers.get('Content-Type')}")
            _logger.info(f"Response Text (if error): {response.text[:500]}")  # Log only first 500 chars

            # Check if content type is an image
            if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
                # Convert the file content to Base64
                base64_encoded = base64.b64encode(response.content).decode('utf-8')
                return f"data:image/png;base64,{base64_encoded}"
            else:
                _logger.error(f"Failed to download file. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            _logger.error(f"Error fetching file: {e}")
            return None
