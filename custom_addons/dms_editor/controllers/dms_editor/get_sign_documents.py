from odoo import http
from odoo.http import request, Response
import math
import json
from odoo.tools import config
from odoo.addons.dms_editor.services.google_storage import LocalStorageService
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)
 
server_path = config['server_path']

class SignDocuments(http.Controller):

    @http.route('/api/file/get-sign-documents', type='http', auth='user', methods=['POST'], csrf=False)
    def get_sign_documents(self, **kwargs):
        try:
            # Parse input parameters
            request_data = json.loads(request.httprequest.data.decode('utf-8'))
            page = int(request_data.get('page', 1))
            per_page = int(request_data.get('per_page', 10))
            email_filter = request_data.get('email', '')
            status_filter = request_data.get('status', '')

            # Get current user details
            user = request.env.user
            user_email = user.email
            user_id = user.id
            _logger.info(f"user_email:{user_email}")
            # Base domain for filtering records
            domain = [
                '|', '|',
                ('email', '=', user_email),
                ('sent_by_email', '=', user_email),
                ('delegate_email', '=', user_email),
                ('status', '!=', 'Draft')
            ]

            # Apply additional filters
            if email_filter:
                domain += [
                    '|', '|',
                    ('email', 'ilike', email_filter),
                    ('sent_by_email', 'ilike', email_filter),
                    ('delegate_email', 'ilike', email_filter)
                ]
            if status_filter:
                domain.append(('status', '=', status_filter))

            # Query documents with pagination
            offset = (page - 1) * per_page
            documents = request.env['document.sign'].sudo().search_read(
                domain, [],
                limit=per_page,
                offset=offset,
                order='create_date desc'
            )

            # Aggregate data by document_id
            aggregated_documents = {}
            for doc in documents:
                doc_id = doc['document_id'][0] if doc['document_id'] else None
                doc_name = doc['document_id'][1] if doc['document_id'] else None
                if doc_id not in aggregated_documents:
                    aggregated_documents[doc_id] = {
                        "id": doc_id,
                        "name": doc_name,
                        "hash_url": doc.get('user_hash', ''),
                        "status": doc.get('status', ''),
                        "document_id": doc_id,
                        "order_by": 0,  # Placeholder, adjust as needed
                        "document_sign": []
                    }

                # Append signature details
                aggregated_documents[doc_id]["document_sign"].append({
                    "id": doc['id'],
                    "date": doc['date'].isoformat() if doc['date'] else None,
                    "email": doc['email'],
                    "reason": doc['reason'],
                    "status": doc['status'],
                    "sent_by": doc['sent_by'],
                    "is_guest": doc['is_guest'],
                    "platform": doc['platform'],
                    "createdat": int(doc['create_date'].timestamp() * 1000) if doc['create_date'] else None,
                    "updatedat": int(doc['write_date'].timestamp() * 1000) if doc['write_date'] else None,
                    "user_hash": doc['user_hash'],
                    "voice_code": doc['voice_code'],
                    "document_id": doc_id,
                    "sms_country": doc['sms_country'] if doc['sms_country'] else "-",
                    "sms_phone_no": doc['sms_phone_no'] if doc['sms_phone_no'] else "",
                    "security_type": doc['security_type'],
                    "sent_by_email": doc['sent_by_email'],
                    "delegate_email": doc['delegate_email'],
                    "number_fill_by": "",
                    "is_last_completed": doc['is_last_completed'],
                    "type": "sent" if doc['sent_by_email'] == user_email else "received",
                    "sent_to": doc['email'] if doc['sent_by_email'] == user_email else None,
                    "sent_to_email": doc['email']
                })

            # Handle specific adjustments for document_sign
            for doc_id, doc_data in aggregated_documents.items():
                # Move current user to the top if order_by is 0
                if doc_data["order_by"] == 0:
                    user_sign = next((ds for ds in doc_data["document_sign"] if ds["email"] == user_email), None)
                    if user_sign:
                        doc_data["document_sign"].remove(user_sign)
                        doc_data["document_sign"].insert(0, user_sign)

                # Add custom logic for is_last_completed
                last_completed = next((ds for ds in doc_data["document_sign"] if not ds["is_last_completed"]), None)
                if last_completed and last_completed["sent_by_email"] != user_email:
                    doc_data["document_sign"].append({
                        "is_owner": True,
                        "status": doc_data["status"],
                        "email": last_completed["sent_by_email"]
                    })

                key_file = f"{server_path}/google_cloud_storage/google_creds.json"
                gcs_service = LocalStorageService()

                # Handle contact and file URL logic
                for ds in doc_data["document_sign"]:
                    if ds["status"] == "Declined" and ds["reason"]:
                        if google_bucket in ds["reason"]:
                            ds["reason"] = gcs_service.read_url(ds["reason"])
                            ds["message_type"] = "voice"
                        else:
                            ds["message_type"] = "message"

                    if ds["status"] == "Signed" and ds["reason"]:
                        ds["verified_voice"] = gcs_service.read_url(ds["reason"])
                        ds["reason"] = ""

                    contact = request.env['res.partner'].sudo().search([('email', '=', ds["email"])], limit=1)
                    if contact:
                        ds["sent_to"] = f"{contact.name} ({contact.email})"
                    else:
                        ds["sent_to"] = ds["email"]

            # Pagination
            total_records = request.env['document.sign'].sudo().search_count(domain)
            total_pages = math.ceil(total_records / per_page)

            # Paginate the aggregated data
            paginated_data = list(aggregated_documents.values())

            # Return response
            response_data = {
                'success': True,
                'total_count': total_records,
                'prev_enable': page > 1,
                'next_enable': page < total_pages,
                'total_pages': total_pages,
                'per_page': per_page,
                'page': page,
                'data': paginated_data
            }
            return Response(json.dumps(response_data), headers={'Content-Type': 'application/json'})

        except Exception as e:
            error_response = {
                'success': False,
                'error': str(e)
            }
            return Response(json.dumps(error_response), headers={'Content-Type': 'application/json'})
