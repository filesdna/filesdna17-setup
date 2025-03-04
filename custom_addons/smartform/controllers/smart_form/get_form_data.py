import base64
import os
import json
import logging
from odoo import http
from odoo.http import request, Response
from odoo.addons.smartform.services.html_to_pdf import PDFService
from odoo.addons.smartform.services.qr_code import generate_branded_qr
from odoo.tools import config

_logger = logging.getLogger(__name__)

 
server_path = config['server_path']


class SmartFormGetFormDataController(http.Controller):

    @http.route('/smartform/get-form-data', type='http', auth='none', methods=['GET'], website=True)
    def form_data(self, **kwargs):
        try:
            # Extract input parameters
            form_hash = kwargs.get('hash')
            if not form_hash:
                return Response(json.dumps({
                    'message': "Hash is required.",
                    'success': False
                }), content_type='application/json', status=400)

            # Fetch the form data
            get_data = PDFService()
            form_data = get_data.get_form_data(form_hash)
            form = request.env['smart.form'].sudo().search([('hash', '=', form_hash)], limit=1)

            if not form:
                return Response(json.dumps({
                    'message': f"No form with hash {form_hash}.",
                    'success': False
                }), content_type='application/json', status=404)

            user = request.env['res.users'].sudo().browse(form.user_id.id)
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')

            # Generate a branded QR code
            logo_path = f'{server_path}/smartform/static/src/images/logo/logo.png'
            public_form_url = f"{base_url}/publicform/{form_hash}"
            qr_output_path = os.path.join('/tmp', f"{form_hash}_qr.png")
            generate_branded_qr(public_form_url, logo_path, qr_output_path)

            # Convert the QR code image to Base64
            with open(qr_output_path, 'rb') as qr_file:
                base64_image = f"data:image/png;base64,{base64.b64encode(qr_file.read()).decode()}"

            # Clean up the generated QR code file
            os.remove(qr_output_path)

            return Response(json.dumps({
                'message': "One form read!",
                'data': form_data,
                'qr': base64_image,
                'user': form.user_id.id,
                'success': True
            }), content_type='application/json', status=200)

        except Exception as e:
            _logger.error(f"Error fetching form data: {str(e)}")
            return Response(json.dumps({
                'message': f"Error: {str(e)}",
                'success': False
            }), content_type='application/json', status=500)
