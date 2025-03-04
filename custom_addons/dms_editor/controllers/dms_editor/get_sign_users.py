import logging
import os
import json
from odoo import http
from datetime import datetime
from odoo.http import request, Response
from odoo.tools import config
from odoo.addons.dms_editor.services.google_storage import LocalStorageService
from odoo.addons.dms_editor.services.helpers import serialize_record

_logger = logging.getLogger(__name__)

 
server_path = config['server_path']

class DocumentSignController(http.Controller):

    @http.route('/api/file/get-sign-users', type='http', auth='user', methods=['POST'], csrf=False)
    def get_sign_users(self, **kwargs):
        try:
            document_id = kwargs.get("document_id")
            if not document_id:
                return Response(
                    json.dumps({"success": False, "message": "Invalid Parameters"}),
                    status=400,
                    mimetype="application/json"
                )

            # Check if the document exists
            document_count = request.env["dms.file"].sudo().search_count([("id", "=", int(document_id))])
            if not document_count:
                return Response(
                    json.dumps({"success": False, "message": "Document not found"}),
                    status=404,
                    mimetype="application/json"
                )

            # Fetch signers' details
            signers = request.env["document.sign"].sudo().search([("document_id", "=", int(document_id))], order="order_by ASC")

            # Process signers
            processed_signers = []
            is_last_completed = 0

            for signer in signers:
                signer_data = {
                    "id": signer.id,
                    "email": signer.email,
                    "delegate_email": signer.delegate_email,
                    "user_hash": signer.user_hash,
                    "order_by": signer.order_by,
                    "status": signer.status,
                    "is_guest": signer.is_guest,
                    "reason": signer.reason,
                    "security_type": signer.security_type,
                    "platform": signer.platform,
                    "voice_code": signer.voice_code,
                    "is_last_completed": signer.is_last_completed,
                    "number_fill_by": signer.number_fill_by,
                    "sms_country": signer.sms_country,
                    "sms_phone_no": signer.sms_phone_no,
                }

                if signer.is_last_completed:
                    is_last_completed = signer.is_last_completed

                # Process reason if it contains a URL
                key_file = f"{server_path}/google_cloud_storage/google_creds.json"
                gcs = LocalStorageService()
                if signer.reason and "/voice" in signer.reason:
                    signer_data["reason"] = gcs.read_url(signer.reason)
                    signer_data["message_type"] = "voice"

                email = signer.email

                # Process delegate user
                if signer.delegate_email:
                    delegate_user = request.env["sign.delegate"].sudo().search(
                        [("email", "=", email), ("is_active", "=", '1')],
                        limit=1,
                    )
                    if delegate_user:
                        delegate_user_data = {
                            "start_date": delegate_user.start_date.strftime("%d-%m-%Y"),
                            "end_date": delegate_user.end_date.strftime("%d-%m-%Y"),
                            "delegate_email": delegate_user.delegate_email,
                            "delegate_first_name": delegate_user.delegate_first_name,
                            "delegate_last_name": delegate_user.delegate_last_name,
                        }
                        signer_data["delegate_user"] = serialize_record(delegate_user_data)
                        email = signer.delegate_email

                # Get user details
                user_details = request.env["res.users"].sudo().search([("email", "=", email)], limit=1)
                if user_details:
                    user_verification, security_setting = self._get_user_security_and_verification(user_details)
                    signer_data["user_verification"] = user_verification
                    signer_data["security_setting"] = {}

                    # Fetch user's contact details
                    contact_details = request.env["res.partner"].sudo().search([("email", "=", email), ("id", "=", user_details.partner_id.id)], limit=1)
                    # signer_data["contact_details"] = serialize_record(contact_details.read()[0]) if contact_details else None

                processed_signers.append(signer_data)

            # Return the processed data
            return Response(
                json.dumps({
                    "success": True,
                    "data": processed_signers,
                    "is_last_completed": is_last_completed,
                }),
                status=200,
                mimetype="application/json"
            )

        except Exception as e:
            _logger.error(f"Error in get_sign_users: {str(e)}")
            return Response(
                json.dumps({"success": False, "message": "An error occurred while processing your request"}),
                status=500,
                mimetype="application/json"
            )


    def _get_user_security_and_verification(self, user_details):
        """Simulate fetching user verification and security settings."""
        # Replace with actual logic to fetch security and verification data
        # user_verification = {
        #     "is_verify_mobile": user_details.is_verify or 0,
        #     "is_verify_id": user_details.is_verify_id or 0,
        #     "is_verify_address": 0,
        #     "is_verify_fingerprint": user_details.finger_print or 0,
        #     "is_verify_uaepass": user_details.is_verify_uaepass or 0,
        #     "is_verify_email": 1,
        #     "is_verify_voice": user_details.is_verify_voice or 0,
        #     "is_verify_liveness": user_details.is_verify_liveness or 0,
        #     "full_name": user_details.first_name + " " + user_details.last_name,
        # }
        # security_setting = {
        #     "two_factor": user_details.two_factor or 0,
        #     "two_factor_microsoft": user_details.two_factor_microsoft or 0,
        #     "finger_print": user_details.finger_print or 0,
        #     "nfc": user_details.nfc or 0,
        #     "six_digit": user_details.six_digit or 0,
        #     "password": 1,
        # }
        user_verify = request.env['user.verification'].sudo().search([('user_id','=',user_details.id)])
        user_verification = {
            "is_verify_voice":  user_verify.is_verify_voice,
            "is_verify_liveness":  user_verify.is_verify_liveness,
        }
        security_setting = {
            "two_factor": 0,
            "two_factor_microsoft": 0,
            "finger_print": 0,
            "nfc": 0,
            "six_digit": 0,
            "password": 1,
        }
        return user_verification, security_setting