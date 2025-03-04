from odoo import http
from odoo.http import request, Response
import json
from odoo.addons.dms_editor.services.email_template import mail_data, notify

class SendDocumentController(http.Controller):
    @http.route('/api/file/send-reminder', type='http', auth='user', methods=['POST'], csrf=False)
    def send_document(self, **kwargs):
        """
        Send a document reminder.

        :param hash_key: The hash key of the document.
        :return: JSON response indicating success or failure.
        """
        request_data = json.loads(request.httprequest.data.decode('utf-8'))
        
        try:
            # Validate user
            user = request.env.user
            if not user:
                return Response(json.dumps({ "message": "Invalid User", "success": False }), headers={'Content-Type': 'application/json'},status=400)

            # Parse inputs
            hash_key = request_data.get('hash_key')
            if not hash_key:
                return Response(json.dumps({ "message": "No hash key found", "success": False }), headers={'Content-Type': 'application/json'},status=400)
            
            # Check if document signature exists
            check_sign = request.env['document.sign'].sudo().search([
                ('user_hash', '=', hash_key),
                ('status', '=', 'Pending')
            ], limit=1)

            if not check_sign:
                return Response(json.dumps({ "message": "No hash key found", "success": False }), headers={'Content-Type': 'application/json'},status=400)
            
            # Check if the file exists
            check_file = request.env['dms.file'].sudo().search([('id', '=', check_sign.document_id.id)], limit=1)
            if not check_file:
                return Response(json.dumps({ "message": "Document not found.", "data": {}, "success": False }), headers={'Content-Type': 'application/json'},status=400)

            # Determine recipient email
            email = check_sign.delegate_email or check_sign.email
            user_data = user
            email_data = request.env['res.users'].sudo().search([('email', '=', email)], limit=1)

            if not email_data:
                email_data_contact = request.env['res.partner'].sudo().search([('email', '=', email)], limit=1)
            else:
                email_data_contact = None

            # Add notification for the recipient
            # if email_data:
            #     request.env['user.notification'].sudo().create({
            #         'type': 'sign-received',
            #         'user_id': email_data.id,
            #         'ip': request.httprequest.remote_addr,
            #         'link': hash_key,
            #         'message': f"Document sent by {user.name} for sign",
            #         'title': f"Reminder for Sign Document - {check_file.name}",
            #         'document_id': check_sign.document_id.id,
            #         'file_data': check_file.file_data,
            #         'source': check_file.source
            #     })
            if email_data:
                notify(email_data.id,f"Reminder for Sign Document - {check_file.name}", 'dms.file', check_file.id)

            # Send email
            mail_data(
                email_type="document_reminder",
                subject=f"Reminder for Sign Document - {check_file.name}",
                email_to= email_data.email,
                header=f"Document sent by {user.name} for sign",
                description=f"You are requested by {user.name} to sign this document.",
                hash_key=hash_key,
            )

            return Response(json.dumps({ "message": "Reminder has been sent", "success": True }), headers={'Content-Type': 'application/json'},status=200)

        except Exception as e:
            return Response(json.dumps({ "message": f"An error occurred: {str(e)}", "success": False }), headers={'Content-Type': 'application/json'},status=500)
