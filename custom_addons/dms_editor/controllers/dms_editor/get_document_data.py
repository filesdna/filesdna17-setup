import os
import logging
import json
from odoo import http
from odoo.http import request, Response
from odoo.tools import config
from odoo.addons.dms_editor.services.qr_code import generate_branded_qr
from odoo.addons.dms_editor.services.email_template import create_log_note

_logger = logging.getLogger(__name__)
 
class DocumentDataController(http.Controller):

    @http.route('/api/files/get-document-data', type='http', auth='public', methods=['POST'], csrf=False)
    def get_document_data(self, **kwargs):
        try:
            # Parameter extraction and validation
            hash_url = kwargs.get('document_id')
            if not hash_url:
                return self._error_response("Invalid Parameters", 400)

            hash_parts = hash_url.split('-')
            if len(hash_parts) != 2:
                return self._error_response("Invalid document identifier format", 400)

            hash_value, timestamp_str = hash_parts
            try:
                current_time = int(timestamp_str)
            except ValueError:
                return self._error_response("Invalid timestamp in document identifier", 400)

            # Document retrieval
            document = request.env['dms.file'].sudo().search([
                ('sha512_hash', '=', hash_value),
                ('current_time_seconds', '=', current_time)
            ], limit=1)

            if not document:
                return self._error_response("Document not found", 404)

            # Document status check
            if document.document_status == "Preparing":
                return Response(json.dumps({'success': True, 'preparing': True}), status=200, mimetype='application/json')

            # User permissions
            user = request.env.user
            is_owner = (document.create_uid.id == user.id)
            write_permission = is_owner
            security_type = document.dms_security_id.name if document.dms_security_id else None

            # QR code management
            qr_code = self._get_or_create_qr_code(kwargs, document)
            if not document.qr_code:
                document.write({'qr_code': qr_code})

            # Response construction
            response_data = {
                'success': True,
                'data': [],  # Placeholder for file pages processing
                'isShare': not is_owner,
                'write': True,
                'bar_code': document.barcode_url,
                'file': {
                    'id': document.id,
                    'integrity': True,
                    'name': document.name,
                    'status': self._map_document_status(document.document_status),
                    'doc_type': "Template" if document.is_template else "Document",
                    'folder_id': document.directory_id.id,
                    'user_id': document.create_uid.id,
                    'folder_ref': 0,
                    'barcode': document.barcode,
                    'ref_number': document.ref_number,
                    'json_version': document.json_version,
                    'qrCode': document.qr_code,
                    'hash_url': f"{document.sha512_hash}-{document.current_time_seconds}"
                },
                'security_type': security_type,
                'signature': [],
                'user_json_version': request.env['dms.json.version'].sudo().search_read(
                    [('document_id', '=', document.id)], ['version']
                ),
            }

            # Log document view
            create_log_note(document.id, f"{user.name} viewed the document")

            return Response(json.dumps(response_data), status=200, mimetype='application/json')

        except Exception as e:
            _logger.error(f"Error retrieving document data: {str(e)}")
            return self._error_response("An error occurred while processing your request.", 500)

    def _get_or_create_qr_code(self, params, document):
        ShareByQr = request.env['share.by.qr'].sudo()
        existing_qr = ShareByQr.search([('document_id', '=', document.id)], limit=1)
        if existing_qr:
            return existing_qr.qr_code

        # Generate new QR code
        hash_key = self._generate_unique_hash()
        is_expire = params.get('is_expire', False)
        expire_time = None
        if is_expire:
            try:
                expire_days = int(params.get('expire_time', 0))
                expire_time = fields.Datetime.now() + timedelta(days=expire_days)
            except ValueError:
                _logger.warning("Invalid expire_time parameter; defaulting to no expiration.")
                is_expire = False

        qr_code = generate_branded_qr(hash_key)
        if qr_code:
            ShareByQr.create({
                'document_id': document.id,
                'share_by': document.create_uid.id,
                'permission': 'view',
                'hash': hash_key,
                'qr_code': qr_code,
                'is_expire': bool(is_expire),
                'expire_time': expire_time,
                'day': 0
            })
        return qr_code

    def _generate_unique_hash(self, length=50):
        import random
        import string
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    def _map_document_status(self, status):
        status_mapping = {
            "in_process": "In Process",
            "pending_owner": "Pending Owner",
            # Add other status mappings as needed
        }
        return status_mapping.get(status, status)

    def _error_response(self, message, status):
        return Response(
            json.dumps({'success': False, 'message': message}),
            status=status,
            mimetype='application/json'
        )
