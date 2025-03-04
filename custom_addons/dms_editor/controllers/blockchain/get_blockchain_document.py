from odoo import http
from odoo.http import request, Response
import json
import math
import logging
from odoo.tools import config
from datetime import datetime

_logger = logging.getLogger(__name__)

class DocumentListController(http.Controller):
    @http.route('/api/file/get-block-chain-doc', type='http', auth='user', methods=['POST'], csrf=False)
    def get_file_list(self, **kwargs):
        try:
            request_data = json.loads(request.httprequest.data.decode('utf-8'))
            user = request.env.user
            user_id = user.id
            blockchain_uid = user.blockchain_uid
            # Input Parameters
            page = int(request_data.get('page', 1))
            per_page = int(request_data.get('per_page', request.env["ir.config_parameter"].sudo().get_param("per_page", default=10)))

            # Count total records grouped by document_id
            count_query = """
                SELECT COUNT(DISTINCT document_id) AS total_records
                FROM document_sign_bc
                WHERE user_id = %s OR owner_id = %s
            """
            request.env.cr.execute(count_query, (blockchain_uid, str(user_id)))
            total_record = request.env.cr.fetchone()[0]

            total_pages = math.ceil(total_record / per_page)
            start_from = (page - 1) * per_page

            # Fetch distinct records on document_id with limit and offset
            select_query = """
                SELECT * FROM (
                    SELECT DISTINCT ON (document_id) *, bc_document AS bc_document
                    FROM document_sign_bc
                    WHERE user_id = %s OR owner_id = %s
                    ORDER BY document_id, create_uid DESC
                ) subquery
                ORDER BY create_uid DESC
                LIMIT %s OFFSET %s
            """
            request.env.cr.execute(select_query, (blockchain_uid, str(user_id), per_page, start_from))
            records = request.env.cr.dictfetchall()

            if records:
                for record in records:
                    # Fetch document name
                    file_data = request.env['dms.file'].sudo().search([('id', '=', record['document_id'])], limit=1)
                    if file_data:
                        record['name'] = file_data.name

                    # Fetch user's public key
                    user_details = request.env['res.users'].sudo().search([('blockchain_uid', '=', record['user_id'])], limit=1)
                    record['pub_key'] = user_details.bc_account if user_details else ''

                    # Parse `bc_document`
                    if 'bc_document' in record and isinstance(record['bc_document'], str):
                        try:
                            corrected_bc_document = json.loads(record['bc_document'].replace("'",'"'))
                        except json.JSONDecodeError:
                            _logger.error(f"Error parsing bc_document for document_id {record['document_id']}")

                    # Add users for the document
                    record['users'] = []
                    grp_users = self._get_users_for_document(record['document_id'], user_id, record.get('email', ''))
                    if grp_users:
                        for user in grp_users:
                            # Parse `bc_document` for each user
                            if 'bc_document' in user and isinstance(user['bc_document'], str):
                                try:
                                    user['bc_document'] = json.loads(user['bc_document'].replace("'",'"'))
                                except json.JSONDecodeError:
                                    _logger.error(f"Error parsing bc_document for user {user['email']}")
                            record['users'].append(user)
            
            
            response_data = {
                "total_count": total_record,
                "prev_enable": 1 if page > 1 else 0,
                "next_enable": 1 if page < total_pages else 0,
                "total_pages": total_pages,
                "per_page": per_page,
                "page": page,
                "data": self.serialize_records(records),
                "success": True,
            }
            return Response(json.dumps(response_data), headers={'Content-Type': 'application/json'}, status=200)

        except Exception as e:
            _logger.error(f"Error fetching file list: {str(e)}")
            return self._response_error(f"An error occurred: {str(e)}")

    def _get_users_for_document(self, document_id, user_id, email):
        try:
            # Check if the current user is the owner of the document
            is_owner = request.env['dms.file'].sudo().search_count([('id', '=', document_id), ('create_uid', '=', user_id)])

            if is_owner:
                return self._get_all_bc_users(document_id, 0)

            # Check for signed and unsigned records
            signed_records = request.env['document.sign'].sudo().search_count([('document_id', '=', document_id), ('order_by', '>', 0)])
            unsigned_records = request.env['document.sign'].sudo().search_count([('document_id', '=', document_id), ('order_by', '=', 0)])

            if signed_records > 0:
                return self._get_all_bc_users(document_id, 0)

            if unsigned_records > 0:
                file_data = request.env['dms.file'].sudo().search([('id', '=', document_id), ('status', '=', 'Completed')], limit=1)
                if file_data:
                    return self._get_all_bc_users(document_id, 0)

            return []

        except Exception as e:
            _logger.error(f"Error fetching users for document {document_id}: {str(e)}")
            return []

    def _get_all_bc_users(self, document_id, record_id):
        try:
            all_users = request.env['document.sign.bc'].sudo().search([
                ('document_id', '=', document_id),
                ('id', '!=', record_id),
                ('hash_value', '!=', '')
            ], order='create_uid ASC')

            result = []
            for idx, user_data in enumerate(all_users, start=1):  # Enumerate to generate the index
                user_details = request.env['res.users'].sudo().search([('blockchain_uid', '=', user_data.user_id)], limit=1)
                delegate_email = ''
                if user_data.email:
                    delegate = request.env['document.sign'].sudo().search([
                        ('document_id', '=', document_id),
                        ('delegate_email', '=', user_data.email)
                    ], limit=1)
                    if delegate:
                        delegate_email = delegate.email

                result.append({
                    'email': user_data.email,
                    'hash_value': user_data.hash_value,
                    'bc_signature': user_data.bc_signature,
                    'user_id': user_data.user_id if user_data.user_id else None,
                    'createdat': int(user_data.create_date.timestamp() * 1000) if user_data.create_date else None,
                    'bc_document': json.loads(user_data.bc_document.replace("'",'"')) if user_data.bc_document else None,
                    'pub_key': json.loads(user_details.bc_account.replace("'",'"'))['pubKey'] if user_details else '',
                    'delegate_email': delegate_email,
                    'index': idx
                })

            return result

        except Exception as e:
            _logger.error(f"Error fetching all blockchain users for document {document_id}: {str(e)}")
            return []

    def _response_error(self, message, status=400):
        return Response(
            json.dumps({
                "success": False,
                "message": message
            }),
            headers={'Content-Type': 'application/json'},
            status=status
        )


    def serialize_records(self,records):
        """
        Serializes datetime objects in a list of records to JSON serializable formats.

        :param records: List of dictionaries containing data with potential datetime objects.
        :return: List of dictionaries with serialized datetime fields.
        """
        for record in records:
            for key, value in record.items():
                # Handle datetime fields
                if isinstance(value, datetime):
                    record[key] = value.isoformat()  # Convert to ISO 8601 string
                # Handle nested lists or dictionaries (e.g., `users`)
                elif isinstance(value, list):
                    record[key] = self.serialize_records(value)  # Recursively process lists
                elif isinstance(value, dict):
                    record[key] = self.serialize_records([value])[0]  # Process dict by wrapping in list
        return records