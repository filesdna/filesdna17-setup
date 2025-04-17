import logging
import json
import os
import base64
from datetime import datetime
from odoo import http
from odoo.http import request, Response
from odoo.tools import config
from odoo.exceptions import UserError
from odoo.addons.dms_editor.services.signers import DocumentSignService
from odoo.addons.dms_editor.services.email_template import mail_data, notify, create_log_note

_logger = logging.getLogger(__name__)

 
class DocumentSendController(http.Controller):

    @http.route('/api/file/send', type='http', auth='user', methods=['POST'], csrf=False)
    def send_document(self, **kwargs):
        try:
            # Extract request parameters
            document_id = kwargs.get("document_id")
            users = json.loads(kwargs.get("users", "[]"))  # Parse JSON users
            is_last_completed = kwargs.get("is_last_completed", False)
            cc_user = kwargs.get("ccuser", "")
            _logger.info(f"document_id:{document_id}")
            _logger.info(f"users:{users}")

            # Validate parameters
            if not document_id or not users:
                return Response(
                    json.dumps({"success": False, "message": "Invalid Parameters"}),
                    status=400,
                    mimetype="application/json"
                )

            # Retrieve the document
            check_file = request.env["dms.file"].sudo().search([("id", "=", document_id)], limit=1)
            if not check_file:
                return Response(
                    json.dumps({"success": False, "message": "Document not found."}),
                    status=404,
                    mimetype="application/json"
                )

            user_details = request.env.user
            for user in users:
                self.send_doc(user, document_id, user_details, check_file, cc_user, is_last_completed)
                create_log_note(document_id, f"Sign request have been sent to {user['email']}")


            # Update document status and version
            _logger.info(f"is_last_completed:{is_last_completed}")
            if is_last_completed:
                request.env["document.sign"].sudo().search([("document_id", "=", document_id)]).write({"is_last_completed": True})

            check_file.write({"document_status": "in_process"})

            return Response(
                json.dumps({"success": True, "message": "Document has been sent to users."}),
                status=200,
                mimetype="application/json"
            )

        except Exception as e:
            _logger.error(f"Error sending document: {str(e)}")
            return Response(
                json.dumps({"success": False, "message": "An error occurred while processing your request."}),
                status=500,
                mimetype="application/json"
            )

    def send_doc(self, item, document_id, user_data, check_file, cc_user, is_last_completed):
        """Send the document to a signer."""
        _logger.info(f"Searching document.sign with document_id: {document_id}, email: {item.get('email')}")

        # Fetch document sign data
        get_data = request.env["document.sign"].sudo().search(
            [("document_id", "=", int(document_id)), ("email", "=", item.get("email"))],
            limit=1
        )
        _logger.info(f"get_data:{get_data}")
        if not get_data:
            return

        # Check if the user is a delegate
        is_delegate = 0
        email = item.get("email")
        if get_data.delegate_email:
            is_delegate = 1
            email = get_data.delegate_email
        _logger.info(f"email:{email}")

        # Update document signer
        is_registered_user = request.env["res.users"].sudo().search([("email", "=", email)], limit=1)
        if not is_registered_user:
            guest = request.env["res.partner"].sudo().search([("email", "=", email)], limit=1)

        get_data.write({
            "ccuser_email": cc_user,
            "is_guest": 0 if is_registered_user else 1,
            "is_last_completed": True if is_last_completed else False
        })

        # Add signer to the document
        order = item.get("order_by", 0)
        sms_content = {
            "number_fill_by": item.get("number_fill_by"),
            "sms_country": item.get("sms_country"),
            "sms_phone_no": item.get("sms_phone_no")
        }
        signer = DocumentSignService()
        signer.add_document_sign_user(
            check_file.id,
            item.get("email"),
            order,
            get_data.is_guest,
            get_data.sent_by,
            "Pending" if order in [0,1] else "Draft",
            user_data.email,
            item.get("security_type"),
            sms_content
        )
        # Send mail to the signer
        hash_key = get_data.user_hash
        if order in [0,1]:
            mail_data(
                email_type="document_sign", 
                subject=f"Sign Document - {check_file.name}", 
                email_to=email, 
                header=f"Hi {is_registered_user.name if is_registered_user else guest.name},", 
                description=f"You are requested by <b>{user_data.name}</b> to sign this document.",
                hash_key=hash_key, 
            )

            # If CC user is provided, send a CC email
            if cc_user:
                mail_data(
                    email_type="document_sign", 
                    subject=f"CC: Invitation from {user_data.name} to sign a document by {is_registered_user.name if is_registered_user else guest.name}",  
                    email_to=cc_user, 
                    header="Hi There,", 
                    description=f"{is_registered_user.name if is_registered_user else guest.name} has been invited to sign this document",
                    hash_key=hash_key,
                )

            if is_registered_user:
                reciever = request.env['res.users'].sudo().search([('email','=',item['email'])], limit=1)
                reciever.notify_info(message=f"You are requested by {user_data.name} to sign the document {check_file.name}.")
                notify(is_registered_user.id,f"You are requested by {user_data.name} to sign this document.", 'dms.file', check_file.id)
        
    def get_nth_tr_str(self, string, index):
        """Extract the nth table row (`<tr>...</tr>`) from the HTML string."""
        start_pos = self.get_position(string, "<tr", index)
        end_pos = self.get_position(string, "</tr>", index)
        if start_pos == -1 or end_pos == -1:
            return ""
        return string[start_pos:end_pos]

    def get_position(self, string, sub_string, index):
        try:
            split_parts = string.split(sub_string, index)
            if len(split_parts) < index:
                return -1  # If the index exceeds occurrences
            return len(sub_string.join(split_parts))
        except Exception as e:
            _logger.error(f"Error in get_position: {str(e)}")
            return -1
