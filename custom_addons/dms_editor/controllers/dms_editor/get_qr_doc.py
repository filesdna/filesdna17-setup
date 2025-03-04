from odoo import http
from odoo.http import request, Response
import json
import logging
from datetime import datetime
from odoo.addons.dms_editor.services.google_storage import LocalStorageService
from odoo.addons.dms_editor.services.helpers import serialize_record
from odoo.tools import config
import os

_logger = logging.getLogger(__name__)
 
server_path = config['server_path']

class QRDocumentController(http.Controller):
    @http.route('/api/get-qrcode-doc', type='http', auth='public', methods=['POST'], csrf=False)
    def get_qr_doc(self, **kwargs):
        try:
            request_data = json.loads(request.httprequest.data.decode('utf-8'))
            params = request_data
            document_id = params.get("document_id")
            action_type = params.get("type")

            if not document_id:
                return self._response_error("Invalid Parameters")

            check_hash = None
            if action_type == "view":
                check_hash = request.env['share.by.qr'].sudo().search([('hash', '=', document_id)], limit=1)
                # if check_hash:
                #     if check_hash.is_expire:
                #         current_timestamp = datetime.now().timestamp() * 1000
                #         if check_hash.expire_time < current_timestamp:
                #             check_hash.sudo().unlink()
                #             return self._response_error("QR code has been expired")
            # elif action_type == "share":
            #     check_hash = request.env['share.document'].sudo().search([('hash_key', '=', document_id)], limit=1)

            if check_hash:
                get_doc_data = request.env['dms.file'].sudo().search([('id', '=', check_hash.document_id.id)], limit=1)
                if get_doc_data:
                    # Attempt to download the file from the bucket
                    key_file = f"{server_path}/google_cloud_storage/google_creds.json"
                    gcs_service = LocalStorageService()
                    temp_dir = f"{server_path}/dms_editor/static/src/temp"
                    local_pdf_path = os.path.join(temp_dir, get_doc_data.attachment_id.store_fname.split('/')[1])
                    db_name= request.env['ir.config_parameter'].sudo().get_param('web.base.url').split("//")[-1].split(".")[0]
                    destination_path = f"{db_name}/{get_doc_data.attachment_id.store_fname}"
                    gcs_service.download_file(destination_path, local_pdf_path, encryption_key=None)

                    # if action_type == "share":
                    #     email_data = self._get_user_by_email(check_hash.share_to)
                    #     sender_data = self._get_user_by_id(check_hash.share_by)
                    #     if not email_data:
                    #         return self._response_success({
                    #             "is_guest": True,
                    #             "sender_name": sender_data.get('name')
                    #         })

                    hash_key = self._generate_random_key(15)
                    request.env['document.load.image'].sudo().create({
                        'doc_image_id': get_doc_data.id,
                        'hash_key': hash_key,
                        'image_type': 'F'
                    })

                    user_details = request.env['res.users'].sudo().search_read(
                        [('id', '=', get_doc_data.create_uid.id)],
                        fields=['email', 'bc_account']
                    )

                    # Fetch document signers
                    document_sign_data = request.env['document.sign'].sudo().search_read(
                        [('document_id', '=', get_doc_data.id), ('status', '=', 'Signed')],
                        fields=['email', 'write_date']
                    )

                    for ds_data in document_sign_data:
                        signer_details = request.env['res.users'].sudo().search_read(
                            [('email', '=', ds_data['email'])],
                            fields=['bc_account']
                        )
                        ds_data['pub_key'] = json.loads(signer_details[0]['bc_account'].replace("'",'"'))['pubKey'] if signer_details else "None"
                        doc_sign_bc = request.env['document.sign.bc'].sudo().search_read(
                            [('email', '=', ds_data['email']), ('document_id', '=', get_doc_data.id)],
                            fields=['bc_signature', 'hash_value']
                        )
                        ds_data['bc_signature'] = doc_sign_bc[0].get('bc_signature') if doc_sign_bc else "None"
                        ds_data['hash_value'] = doc_sign_bc[0].get('hash_value') if doc_sign_bc else "None"
                        write_date = ds_data.get('write_date')
                        _logger.info(f"int(write_date.timestamp() * 1000):{int(write_date.timestamp() * 1000)}")

                        # Override write_date with updatedat
                        if 'write_date' in ds_data:
                            # Convert write_date to timestamp in milliseconds for updatedat
                            ds_data['updatedAt'] = int(ds_data['write_date'].timestamp() * 1000)
                            # Remove the original write_date key
                            del ds_data['write_date']

                    # Add additional fields to the `get_doc_data` dictionary
                    get_doc_data_dict = {
                        'id': get_doc_data.id,
                        'name': get_doc_data.name,
                        'status':get_doc_data.document_status,
                        'write': action_type == "share" and check_hash.permission == "Write",
                        'permission': check_hash.permission,
                        'url': f"{request.env['ir.config_parameter'].sudo().get_param('web.base.url')}/api/get-detail-view/{hash_key}",
                        'email': user_details[0].get('email') if user_details else None,
                        'signers': document_sign_data  # Include signers if they are calculated
                    }
                    return self._response_success(get_doc_data_dict)

                else:
                    return self._response_error("No document found")
            else:
                message = "QR code has been expired" if action_type == "view" else "Link is not valid anymore"
                return self._response_error(message)

        except Exception as e:
            _logger.error(f"Error in get_qr_doc: {str(e)}")
            return self._response_error("An error occurred while processing the request")

    def _response_error(self, message, change=False):
        return Response(
            json.dumps({
                "success": False,
                "message": message,
                "change": change
            }),
            headers={'Content-Type': 'application/json'},
            status=400
        )

    def _response_success(self, data):
        return Response(
            json.dumps({
                "success": True,
                "data": data
            }),
            headers={'Content-Type': 'application/json'},
            status=200
        )

    def _get_user_by_email(self, email):
        # Dummy implementation for fetching user by email
        return {"email": email, "name": "Dummy User"}

    def _get_user_by_id(self, user_id):
        # Dummy implementation for fetching user by ID
        return {"id": user_id, "name": "Dummy Sender"}

    def _generate_random_key(self, length):
        import random
        import string
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
