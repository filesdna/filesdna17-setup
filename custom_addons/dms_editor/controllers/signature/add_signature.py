from odoo import http
from odoo.http import request, Response
from datetime import datetime
import json
import hashlib
import base64
import logging
from odoo.addons.dms_editor.services.signature import SignatureHelper
from odoo.addons.dms_editor.services.user import User
from odoo.tools import config

_logger = logging.getLogger(__name__)

sign = SignatureHelper()
user_sign = User()

server_path = config['server_path']


def serialize_data(record):
    for key, value in record.items():
        if isinstance(value, datetime):
            record[key] = value.isoformat()
    return record

class CreateUserSignatureController(http.Controller):

    @http.route('/api/user/add-signature', type='http', auth='user', methods=['POST'], csrf=False)
    def create_signature(self, **kwargs):
        """
        Create a user signature.

        :param kwargs: JSON payload with signature details.
        :return: JSON response indicating success or failure.
        """
        try:
            request_data = json.loads(request.httprequest.data.decode('utf-8'))
            # Parse inputs
            user = request.env.user
            user_id = user.id
            user_email = user.email
            user_name = user.name

            # generate hash for signature
            hash_key = self.calculate_file_hash(user_name, "base64")
            
            inputs = request_data

            if not inputs.get('type') or inputs['type'] not in ['choose', 'draw', 'upload']:
                return Response(json.dumps({
                    "message": "Invalid signature type provided.",
                    "success": False
                }), headers={'Content-Type': 'application/json'},status=400)

            existing_signatures_count = request.env['user.signature'].sudo().search_count([('user_id', '=', user_id)])

            # Handle different signature creation types
            if inputs['type'] == 'choose':
                try:
                    # Check if signature already exists
                    existing_signature = request.env['user.signature'].sudo().search([
                        ('full_name', '=', inputs.get('full_name')),
                        ('user_id', '=', user_id)
                    ], limit=1)

                    signature_font = f"sign{str(inputs.get('signature_font'))}" if inputs.get('signature_font') != "roboto" else "roboto"
                    full_sign = sign.upload_signature(
                        name=inputs.get('full_name', user_name),
                        font_path=f"{server_path}/dms_editor/static/src/fonts/{signature_font}.ttf",
                        sign_type="full",
                        sign_by=inputs.get('sign_by', user_name),
                        date= inputs.get('date', ''),
                        reason=inputs.get('reason', ""),
                        no_design='0' if inputs.get('no_design') else '1',
                        base64_output=False
                    )

                    initial_sign = sign.upload_signature(
                        name=inputs.get('initial_name', user_name),
                        font_path=f"{server_path}/dms_editor/static/src/fonts/{signature_font}.ttf",
                        sign_type="initial",
                        sign_by="",
                        date="",
                        reason="",
                        no_design='0' if inputs.get('no_design') else '1',
                        base64_output=False
                    )
                    
                    inputs['full_signature'] = full_sign['image']
                    inputs['initial_signature'] = initial_sign['image']
                    inputs['signature_hash'] = full_sign['hash']
                except Exception as e:
                    _logger.error(f"An error occurred when uploading signature: {str(e)}")
                    return Response(json.dumps({
                        "message": f"An error occurred when uploading signature: {str(e)}",
                        "success": False
                    }), headers={'Content-Type': 'application/json'},status=500)

                if existing_signature:
                    try:
                        # Update existing signature
                        sign.remove_old_signature(existing_signature.full_signature,"choose")
                        sign.remove_old_signature(existing_signature.initial_signature,"choose")
                        existing_signature.write({
                            'full_signature': inputs.get('full_signature'),
                            'initial_signature': inputs.get('initial_signature'),
                            'signature_font': inputs.get('signature_font'),
                            'sign_by': inputs.get('sign_by', user_name),
                            'type':inputs['type'],
                            'date': inputs.get('date', ''),
                            'reason': inputs.get('reason', ''),
                            'default': '1' if existing_signatures_count == 0 else '0',
                        })

                        # Log audit
                        # request.env['audit.log'].sudo().create({
                        #     'user_id': user_id,
                        #     'message': f"You updated a signature.",
                        #     'event_type': 'signature',
                        #     'event_date': datetime.now(),
                        # })
                        data = existing_signature.read()[0]
                        serialized_data = serialize_data(data)
                        return Response(json.dumps({
                            "message": "Signature has been updated successfully.",
                            "data": serialized_data,
                            "success": True
                        }), headers={'Content-Type': 'application/json'},status=200)

                    except Exception as e:
                        _logger.error(f"An error occurred when updating signature: {str(e)}")
                        return Response(json.dumps({
                            "message": f"An error occurred when updating signature: {str(e)}",
                            "success": False
                        }), headers={'Content-Type': 'application/json'},status=500)
                
                else:
                    try:
                        # Create a new signature
                        new_signature = request.env['user.signature'].sudo().create({
                            'user_id': user_id,
                            'full_name': inputs.get('full_name', ''),
                            'initial_name': inputs.get('initial_name', ''),
                            'full_signature': inputs.get('full_signature'),
                            'type':inputs['type'],
                            'initial_signature': inputs.get('initial_signature'),
                            'signature_hash':hash_key,
                            'signature_font': inputs.get('signature_font'),
                            'sign_by': inputs.get('sign_by', user_name),
                            'date': inputs.get('date', ''),
                            'reason': inputs.get('reason', ''),
                            'default': '1' if existing_signatures_count == 0 else '0',
                        })

                        # Log audit
                        # request.env['audit.log'].sudo().create({
                        #     'user_id': user_id,
                        #     'message': f"You created a signature.",
                        #     'event_type': 'signature',
                        #     'event_date': datetime.now(),
                        # })
                        data = new_signature.read()[0]
                        serialized_data = serialize_data(data)
                        return Response(json.dumps({
                            "message": "Signature has been added successfully.",
                            "data": serialized_data,
                            "success": True
                        }), headers={'Content-Type': 'application/json'},status=200)
                        
                    except Exception as e:
                        _logger.error(f"An error occurred when adding signature: {str(e)}")
                        return Response(json.dumps({
                            "message": f"An error occurred when adding signature: {str(e)}",
                            "success": False
                        }), headers={'Content-Type': 'application/json'},status=500)

            elif inputs['type'] in ['draw', 'upload']:
                try:
                    
                    # generate the full signature image as base64 
                    generated_full_signature = sign.generate_html_signature_base64(
                        inputs.get('signature',''),
                        hash_key,
                        "full",
                        user_name,
                        inputs.get('date', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')),
                        inputs.get('reason', ""),
                        '0' if inputs.get('no_design') else '1'
                    )

                    # upload the full signature to bucket and return url
                    full = user_sign.upload_file(avtar=generated_full_signature)

                    # generate the initial signature image as base64 
                    generated_initial_signature = sign.generate_html_signature_base64(
                        inputs.get('initial',''),
                        "",
                        "initial",
                        "",
                        "",
                        "",
                        '0' if inputs.get('no_design') else '1'
                    )
                    _logger.info(f'generated_full_signature:{generated_full_signature}')
                    # upload the initial signature to bucket and return url
                    initial = user_sign.upload_file(avtar=generated_initial_signature)

                    # Create the signature record
                    new_signature = request.env['user.signature'].sudo().create({
                        'user_id': user_id,
                        'full_name': '',
                        'type':inputs['type'],
                        'initial_name': '',
                        'full_signature': full,
                        'initial':generated_initial_signature,
                        'signature':generated_full_signature,
                        'signature_hash': hash_key,
                        'initial_signature': initial,
                        'signature_font': inputs.get('signature_font'),
                        'sign_by': inputs.get('sign_by', user_name),
                        'date': inputs.get('date', ''),
                        'reason': inputs.get('reason', ''),
                        'default': '1' if existing_signatures_count == 0 else '0',
                    })

                    # Log audit
                    # request.env['audit.log'].sudo().create({
                    #     'user_id': user_id,
                    #     'message': f"You created a signature.",
                    #     'event_type': 'signature',
                    #     'event_date': datetime.now(),
                    # })
                    
                    data = new_signature.read()[0]
                    serialized_data = serialize_data(data)
                    return Response(json.dumps({
                        "message": "Signature has been added successfully.",
                        "data": serialized_data,
                        "success": True
                    }), headers={'Content-Type': 'application/json'},status=200)

                except Exception as e:
                    _logger.error(f"An error occurred when uploading or drawing a signature: {str(e)}")
                    return Response(json.dumps({
                        "message": f"An error occurred when uploading or drawing a signature: {str(e)}",
                        "success": False
                    }), headers={'Content-Type': 'application/json'},status=500)
            else:
                return Response(json.dumps({
                    "message": "Invalid signature type.",
                    "success": False
                }), headers={'Content-Type': 'application/json'},status=400)

        except Exception as e:
            _logger.error(f"Error in create_signature: {str(e)}")
            return Response(json.dumps({
                "message": f"An error occurred: {str(e)}",
                "success": False
            }), headers={'Content-Type': 'application/json'},status=500)


    def calculate_file_hash(self, data, encoding):
        """ Placeholder for calculating file hash """
        # Simulate hash calculation
        return hashlib.sha512(data.encode()).hexdigest()

    def format_input_date(self,input_date):
        """
        Format the input date string to '%Y-%m-%d %H:%M:%S'.
        If the input is already in that format, return it as is.
        """
        try:
            # Attempt to parse the input date in multiple formats
            return datetime.strptime(input_date, '%d/%m/%Y %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')  # Default fallback to current UTC time