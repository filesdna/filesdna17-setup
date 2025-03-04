from odoo import http
from odoo.http import request, Response
import json
from datetime import datetime
from odoo.addons.dms_editor.services.email_template import mail_data, notify

class CancelSignProcessController(http.Controller):
    @http.route('/api/file/cancel-sign-process', type='http', auth='user', methods=['POST'], csrf=False)
    def cancel_sign_process(self, **kwargs):
        """
        Cancel the sign process for a document.

        :param document_id: ID of the document to cancel the sign process for.
        :return: JSON response indicating success or failure.
        """
        try:
            request_data = json.loads(request.httprequest.data.decode('utf-8'))
            # Parse the input
            document_id = request_data.get('document_id')
            if not document_id:
                return Response(json.dumps({ "message": "Missing params.", "data": {}, "success": False }), headers={'Content-Type': 'application/json'},status=400)

            # Get current user details
            user = request.env.user
            user_id = user.id
            user_email = user.email
            user_name = user.name

            # Check if the document exists and belongs to the user
            dms_file = request.env['dms.file'].sudo().search([('id', '=', document_id), ('create_uid', '=', user_id)], limit=1)
            if not dms_file:
                return Response(json.dumps({ "message": "Document not found.", "success": False }), headers={'Content-Type': 'application/json'},status=400)
            
            # Fetch related document sign records
            document_signs = request.env['document.sign'].sudo().search([('document_id', '=', document_id)])
            
            # Delete the document sign records
            document_signs.sudo().unlink()

            # Remove document signer data (placeholder for custom functionality)
            # Replace 'remove_doc_signer' with your Odoo equivalent logic
            # request.env['dms.file'].sudo().remove_doc_signer(document_id)

            # Update counts for sender and receiver
            for doc_sign in document_signs:
                # Update counts for sender
                # request.env['dms.file'].sudo().update_sent_request_counts(dms_file.user_id, doc_sign.sent_by_email)

                # Update counts for receiver
                receiver_data = request.env['res.users'].sudo().search([('email', '=', doc_sign.email)], limit=1)
                if receiver_data:
                    notify(receiver_data.id, f"Document {dms_file.name} sign request have been canceled by {user_name}",'dms.file',dms_file.id)
                mail_data(
                    email_type="public", 
                    subject=f"Sign Request Canceled - {dms_file.name}", 
                    email_to=receiver_data.email, 
                    header=f"Hi {receiver_data.name},", 
                    description=f"You are requested by <b>{user_name.name}</b> to sign this document.",
                    hash_key=hash_key, 
                )
            # Log audit events
            # user_ip = request.httprequest.remote_addr
            # request.env['audit.history'].sudo().create({
            #     'user_id': user_id,
            #     'document_id': document_id,
            #     'message': "Document sign process cancelled by",
            #     'name': user_name,
            #     'ip_address': user_ip,
            #     'type': "update",
            # })

            # request.env['audit.event'].sudo().create({
            #     'user_id': user_id,
            #     'description': f"You cancelled the sign process of document <b>{dms_file.name}</b> from IP: <b>{user_ip}</b>",
            #     'event_type': "request",
            #     'event_date': datetime.now(),
            #     'extra_info': "",
            # })

            # Update the document's status to "Draft"
            dms_file.sudo().write({'status': 'Draft'})
            return Response(json.dumps({ "message": "Sign process has been cancelled", "success": True }), headers={'Content-Type': 'application/json'},status=200)

        except Exception as e:
            return Response(json.dumps({ "message": f"An error occurred: {str(e)}", "success": False }), headers={'Content-Type': 'application/json'},status=500)
