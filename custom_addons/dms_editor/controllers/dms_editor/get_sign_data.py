import logging
import json
from odoo import http
from odoo.http import request, Response
from odoo.addons.dms_editor.services.files import Files
from odoo.addons.dms_editor.services.helpers import serialize_record

_logger = logging.getLogger(__name__)

class DocumentSignController(http.Controller):

    @http.route('/api/files/get-sign-data', type='http', auth='public', methods=['POST'], csrf=False)
    def get_sign_data(self, **kwargs):
        try:
            # Extract hash_key from parameters
            hash_key = kwargs.get("hash_key")
            if not hash_key:
                return Response(
                    json.dumps({"success": False, "message": "Invalid hash key"}),
                    status=400,
                    mimetype="application/json"
                )

            # Find the document sign entry using the hash_key
            check_hash = request.env["document.sign"].sudo().search([
                ("user_hash", "=", hash_key)
            ], limit=1)

            if not check_hash:
                return Response(
                    json.dumps({"success": False, "message": "Invalid hash key"}),
                    status=404,
                    mimetype="application/json"
                )

            # Handle signed or declined status
            if check_hash.status == "Signed":
                return Response(
                    json.dumps({"success": False, "already_signed": True}),
                    status=200,
                    mimetype="application/json"
                )
            elif check_hash.status == "Declined":
                return Response(
                    json.dumps({
                        "message": "Document declined, Please contact the document owner",
                        "success": False,
                        "declined": True
                    }),
                    status=200,
                    mimetype="application/json"
                )

            # Retrieve the associated document
            document = request.env["dms.file"].sudo().search([
                ("id", "=", check_hash.document_id.id)
            ], limit=1)

            if not document:
                return Response(
                    json.dumps({"success": False, "message": "Document not found"}),
                    status=404,
                    mimetype="application/json"
                )

            # Determine the email to use (delegate or original)
            if check_hash.delegate_email == request.env.user.email:
                email = check_hash.delegate_email
            else:
                email = check_hash.email

            # Retrieve user details
            user_details = request.env["res.users"].sudo().search([
                ("email", "=", email)
            ], limit=1)

            is_guest = 0 if user_details else 1
            security_setting = {}

            # If the user exists, prepare security settings
            if user_details:
                if email != request.env.user.email:
                    return Response(
                        json.dumps({"success": False, "message": "you dont have permission to access this document"}),
                        status=401,
                        content_type="application/json"
                    )
                user_verification = request.env['user.verification'].sudo().search([('user_id','=',request.env.user.id)],limit=1)
                security_setting = {
                    "two_factor": 0,
                    "finger_print": 0,
                    "nfc": 0,
                    "six_digit": 0,
                    "two_factor_microsoft": 0,
                    "is_verify_voice": user_verification.is_verify_voice if user_verification else 0,
                    "is_verify_liveness": user_verification.is_verify_liveness if user_verification else 0,
                }

                if check_hash.security_type and not security_setting.get(check_hash.security_type, False):
                    return Response(
                        json.dumps({
                            "success": True,
                            "security_not_enabled": check_hash.security_type,
                            "data": [],
                            "user": serialize_record(check_hash.read()[0])
                        }),
                        status=200,
                        mimetype="application/json"
                    )

            # Log activity
            # request.env["dms.activity.log"].sudo().create({
            #     "user_id": document.user_id.id,
            #     "document_id": document.id,
            #     "message": f"Document viewed by {email}",
            #     "ip_address": request.httprequest.remote_addr,
            #     "type": "viewed"
            # })

            # Generate images for the document
            file_service = Files()
            images = file_service.generate_images_with_hash(
                document.id, document.document_status, False
            )

            # Prepare the response data
            response_data = {
                "data": images,
                "signs": [],
                "user": serialize_record(check_hash.read()[0]),
                "file": {
                    "name": document.name,
                    "hash": document.sha512_hash,
                    "id": document.id,
                    "user_id": document.create_uid.id
                },
                "sign_hash": hash_key,
                "security_setting": security_setting,
                "is_guest": is_guest,
                "security_type": check_hash.security_type,
                "number_fill_by": check_hash.number_fill_by,
                "sms_country": check_hash.sms_country,
                "sms_phone_no": check_hash.sms_phone_no,
                "success": True
            }

            return Response(
                json.dumps(response_data),
                status=200,
                mimetype="application/json"
            )

        except Exception as e:
            _logger.error(f"Error in get_sign_data: {str(e)}")
            return Response(
                json.dumps({"success": False, "message": "An error occurred while processing your request"}),
                status=500,
                mimetype="application/json"
            )
