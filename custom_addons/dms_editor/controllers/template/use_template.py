from odoo import http
from odoo.http import request
import json
from datetime import datetime
import random
import logging
import string
from odoo.addons.dms_editor.services.template import TemplateService 
from odoo.addons.dms_editor.services.helpers import serialize_record
from odoo.addons.dms_editor.services.signers import DocumentSignService
from odoo.addons.dms_editor.services.email_template import mail_data, notify

from odoo.tools import config

_logger = logging.getLogger(__name__)

template_service = TemplateService()
signers_service = DocumentSignService()

class CreateDocumentController(http.Controller):
    @http.route('/api/template/use', type='json', auth='user', methods=['POST'], csrf=False)
    def use_template(self, **kwargs):
        """
        API to create a document from a template, assign roles, and manage workflow.

        :param name: The name of the document.
        :param template_id: The ID of the template.
        :param assign_roles: JSON of roles to assign.
        :param apiAry: JSON of API data.
        :param type: Document type (optional).
        :param is_last_completed: Whether it's the last completed document.
        :param folder_id: Folder ID to store the document (optional).
        """
        try:
            # Get the current user
            user = request.env.user
            user_id = user.id
            user_email = user.email

            # Extract inputs
            name = kwargs.get('name')
            template_id = kwargs.get('template_id')
            assign_roles = kwargs.get('assign_roles')
            apiAry = kwargs.get('apiAry')
            doc_type = kwargs.get('type')
            is_last_completed = kwargs.get('is_last_completed', False)
            folder_id = kwargs.get('folder_id', 1)
            
            if not name or not template_id or not assign_roles or not apiAry:
                return {"success": False, "message": "Missing required parameters."}

            # Validate template
            template = request.env['template.roles'].sudo().search([('template_id', '=', template_id)], limit=1)
            if not template:
                return {"success": False, "message": "Template not found."}
            
            # Process roles
            roles = [
                {
                    "id": role.get('id'),
                    "name": role.get('name'),
                    "color": role.get('color', None),
                }
                for element in apiAry if (role := element.get('role')) and isinstance(role, dict) and role.get('id') is not None
            ]
            # Deduplicate roles
            roles = {r['id']: r for r in roles}.values()
            

            # Determine if the document is for the user themselves
            is_myself = len(roles) == 1 and any(r['id'] == 0 for r in roles)
            
            document = template_service.template_copy_pdf(template_id, name, user, assign_roles, apiAry, folder_id, is_myself)
            
            document_data = request.env['dms.file'].sudo().search([('id', '=', document['id'])], limit=1)
            
            for role_key, role_data in assign_roles.items():
                if int(role_key) != 0:
                    
                    self._send_doc(role_data, document_data.id, user, document_data)

            # Update document status and additional actions if needed
            document_data.write({'document_status': 'in_process', 'write_uid': f"{user_id}"})
            if is_last_completed:
                request.env['document.sign'].sudo().search([('document_id', '=', document_data.id)]).write({
                    'is_last_completed': True,
                })

            if is_myself:
                # Assign the document to the current user for signing
                sign_vals = {
                    'document_id': document_data.id,
                    'email': user_email,
                    'user_hash': ''.join(random.choices(string.ascii_letters + string.digits, k=40)),
                    'order_by': 0,
                    'is_guest': 0,
                    'status': 'Pending',
                    'sent_by': user.name,
                    'sent_by_email': user_email,
                    'date': datetime.now().strftime("%Y-%m-%d"),
                    'is_last_completed': is_last_completed,
                }
                request.env['document.sign'].sudo().create(sign_vals)
                return {
                    "success": True,
                    "message": "Document has been sent to you.",
                    "is_myself": True,
                    "docData": {
                        **serialize_record(document_data.read()[0]), 
                        "json_data": document['json_data']
                        },
                }

            return {
                "success": True,
                "message": "Document has been sent to users.",
                "docData":{
                    "id": document_data.id
                }
            }

        except Exception as e:
            _logger.error(f"Error in template use: {str(e)}")
            return {"success": False, "message": f"An error occurred: {str(e)}"}

    def _send_doc(self, item, document_id, user_data, check_file, ip=''):
        """
        Send document to a user for signing.

        :param item: Dictionary containing document sign object.
        :param document_id: ID of the document.
        :param user_data: Dictionary containing user details.
        :param check_file: Dictionary containing document details.
        :param ip: IP address (optional).
        :return: Boolean indicating success.
        """
        try:
            is_delegate = 0
            email = item.get('email')
            # Retrieve document sign data
            get_data = request.env['document.sign'].sudo().search(
                [('document_id', '=', document_id), ('email', '=', email)],
                limit=1
            )

            if get_data and get_data.delegate_email:
                is_delegate = 1
                email = get_data.delegate_email

            order = int(item.get('order_by', 0))
            
            is_registered_user = request.env['res.users'].sudo().search([('email', '=', email)], limit=1)
            is_guest = get_data.is_guest if get_data else (0 if is_registered_user else 1)
            sent_by = get_data.sent_by if get_data else user_data.name

            sms_content = {
                'number_fill_by': item.get('number_fill_by') or '',
                'sms_country': item.get('sms_country') or '',
                'sms_phone_no': item.get('sms_phone_no') or '',
            }

            # Add document sign user
            get_data = signers_service.add_document_sign_user(
                check_file.id,
                email, 
                order, 
                is_guest, 
                sent_by, 
                'Pending' if order == 0 or order == 1 else 'Draft', 
                user_data.email, 
                item.get('security_type'), 
                sms_content
            )

            # Prepare email content
            hash_key = get_data.user_hash
            receiver_name = item.get('first_name', '') or get_data.email

            # Send email
            if order in [0, 1]:
                mail_data(
                    email_type="document_sign", 
                    subject=f"Sign Document - {check_file.name}", 
                    email_to=email, 
                    header=f"Hi {receiver_name},", 
                    description=f"You are requested by <b>{user_data.name}</b> to sign this document.",
                    hash_key=hash_key,
                )
                if is_registered_user:
                    notify(is_registered_user.id, f"You are requested by {user_data.name} to sign this document.", 'dms.file', check_file.id)

                # Add activity log
                # log_message = f"Document (Sign Request) sent to {receiver_name}."
                # request.env['activity.log'].sudo().create({
                #     'user_id': check_file.user_id.id,
                #     'document_id': document_id,
                #     'message': log_message,
                #     'name': receiver_name,
                #     'ip_address': ip,
                #     'type': 'sent',
                # })

                # Send notification to the user
                # email_data = request.env['res.partner'].sudo().search(
                #     [('email', '=', email)],
                #     limit=1
                # )
                # if email_data:
                #     notification_data = {
                #         'type': 'sign-received',
                #         'user_id': email_data.id,
                #         'ip': ip,
                #         'link': hash_key,
                #         'message': f"Document sent by {user_data['first_name']} {user_data['last_name']} for signing.",
                #         'title': f"Sign Document - {check_file.name}",
                #         'document_id': document_id,
                #     }
                #     request.env['notification.log'].sudo().create(notification_data)

            return True

        except Exception as e:
            _logger.error(f"Error in send_doc: {str(e)}")
            return False
