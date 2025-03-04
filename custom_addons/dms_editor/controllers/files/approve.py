import logging
import json
import time
from odoo import http
from odoo.http import request
from odoo.tools import config
from odoo.addons.dms_editor.services.files import Files
from odoo.addons.dms_editor.services.email_template import mail_data, notify, create_log_note
from odoo.addons.workflow.services.helpers import WorkflowHelper
from odoo.addons.workflow.services.workflow_nodes.check_next_node import CheckNextNode

_logger = logging.getLogger(__name__)

workflow_helper = WorkflowHelper()
check_next_node = CheckNextNode()
class DocumentApproveController(http.Controller):

    @http.route('/api/file/approve', type='json', auth='public', methods=['POST'])
    def approve_document(self, **kwargs):
        try:
            # Extract inputs
            hash_key = kwargs.get("hash")
            json_data = kwargs.get("json_data")
            timezone = kwargs.get("timezone", "")
            platform = kwargs.get("platform", "website")
            logged_user = kwargs.get("user", {})
            is_valid_user = True if (logged_user.get('email') == 'public' or logged_user.get('email') == False) else  False

            # Validate user
            update_status = request.env['document.sign'].sudo().search([
                ('user_hash', '=', hash_key),
                ('status', '=', 'Pending')
            ], limit=1)

            if not update_status:
                return {"message": "Hash not found", "success": False}

            contacts_detail = request.env['res.partner'].sudo().search([
                ('email', '=', update_status.delegate_email or update_status.email)
            ], limit=1)

            # Update is_valid_user based on the found contact details
            if is_valid_user and contacts_detail:
                is_valid_user = True
            else:
                user_detail = request.env['res.users'].sudo().search([ ('email', '=', update_status.delegate_email or update_status.email) ], limit=1)
                _logger.info(f"user_detail:{user_detail}")
                is_valid_user = True if user_detail else False

            if not is_valid_user:
                return {"message": "Unauthorized!", "success": False}

            # Fetch file data
            file_data = request.env['dms.file'].sudo().search([
                ('id', '=', update_status.document_id.id)
            ], limit=1)
            status = None
            if not file_data:
                return {"message": "File not found", "success": False}

            ip_address = request.httprequest.remote_addr

            user_details = request.env['res.users'].sudo().search([
                ('id', '=', file_data.create_uid.id)
            ], limit=1)
            # if user_details:
            #     user_details.update_user_tracking_data({'column': 'signed_files_cnt'})

            # # Add activity log
            # request.env['activity.log'].sudo().create({
            #     'user_id': file_data.user_id,
            #     'document_id': update_status.document_id,
            #     'message': f"Document signed by {logged_user.get('email')}",
            #     'ip_address': ip_address,
            #     'type': 'signed',
            #     'file_data': file_data.file_data,
            #     'source': file_data.source
            # })

            # Check order and update status

             # Handle order-based signing logic
            replace = False
            pass_check = False

            if update_status.order_by > 0:
                # Handle the next signer
                next_signer = request.env['document.sign'].sudo().search([
                    ('order_by', '=', update_status.order_by + 1),
                    ('document_id', '=', update_status.document_id.id)
                ], limit=1)
                _logger.info(f"next_signer:{next_signer}")
                if next_signer:
                    _logger.info(f"next_signer:{next_signer.email}")
                    hash_link = next_signer.user_hash
                    receiver_user = request.env["res.partner"].sudo().search([("email", "=", next_signer.email)], limit=1)
                    mail_data(
                        email_type="document_sign", 
                        subject=f"Sign Document - {file_data.name}",  
                        email_to=next_signer.delegate_email or next_signer.email,
                        header=f"Hi {receiver_user.name},", 
                        description=f"You are requested by <b>{user_details.name}</b> to sign this document.",
                        hash_key=hash_link,
                    )
 
                    registered_user = request.env["res.users"].sudo().search([("email", "=", next_signer.email)], limit=1)
                    if registered_user:                   
                        notify(registered_user.id,f"You are requested by {user_details.name} to sign this document.", 'dms.file', file_data.id)
                    
                    next_signer.write({'status': 'Pending'})
                    # Notify next signer
                    # notification_data = {
                    #     'type': "sign-received",
                    #     'user_id': next_signer.user_id,
                    #     'ip': ip_address,
                    #     'link': hash_link,
                    #     'message': f"Document sent by {user_details.first_name} {user_details.last_name}",
                    #     'title': f"Sign Document - {file_data.name}",
                    #     'document_id': file_data.id,
                    #     'file_data': file_data.file_data,
                    #     'source': file_data.source
                    # }
                    # request.env['notification.log'].sudo().create(notification_data)


                # Determine document status
                last_sign_data = request.env["document.sign"].sudo().search([
                    ("document_id", "=", update_status.document_id.id)
                ], order="order_by DESC", limit=1)

                if last_sign_data and last_sign_data.order_by == update_status.order_by:
                    status = "Completed" if update_status.is_last_completed else "pending_owner"
                else:
                    status = "in_process"

                replace = True
            else:
                all_sign_count = request.env["document.sign"].sudo().search_count([
                    ("document_id", "=", update_status.document_id.id),
                    ("order_by", "=", 0)
                ])
                signed_count = request.env["document.sign"].sudo().search_count([
                    ("document_id", "=", update_status.document_id.id),
                    ("order_by", "=", 0),
                    ("status", "=", "Signed")
                ]) + 1
                if all_sign_count == signed_count:
                    status = "Completed" if update_status.is_last_completed else "pending_owner"
                    pass_check = True
                else:
                    status = "in_process"

                replace = True

            # Update document sign status
            update_status.write({
                "status": "Signed",
                "platform": platform
            })

            # Add activity log
            # request.env["activity.log"].sudo().create({
            #     "user_id": file_data.user_id,
            #     "document_id": update_status.document_id,
            #     "message": "Document Signed",
            #     "name": contacts_detail.email,
            #     "email": update_status.email,
            #     "ip_address": ip_address,
            #     "type": "signed",
            #     "file_data": file_data.file_data,
            #     "source": file_data.source
            # })

            # Generate new PDFs if necessary
            if replace:
                email = update_status.delegate_email or update_status.email
                get_cuser = request.env["res.users"].sudo().search([("email", "=", email)], limit=1)
                get_cpartner = None  # Ensure get_cpartner is initialized

                if not get_cuser:
                    get_cpartner = request.env["res.partner"].sudo().search([("email", "=", email)], limit=1)

                if get_cuser:
                    is_guest = 0
                    email = get_cuser.email
                    user_id = get_cuser.blockchain_uid
                    # Add events (audit logs)
                    # request.env["audit"].sudo().add_event(user_id, f"Signed document {file_data.name} from IP {ip_address}", "request")
                else:
                    email = get_cpartner.email
                    user_id = file_data.create_uid.blockchain_uid
                    is_guest = 1

                # Generate new PDFs
                file_service = Files()
                json_filtered = [item for item in json_data if item.get("hash") == hash_key]
                try:
                    file_service.generate_new_pdf(
                        file_data, status, user_id, is_guest, timezone, email, ip_address, get_cuser or get_cpartner, json_filtered
                    )
                except Exception as e:
                    _logger.error(f"Error in generate new pdf: {str(e)}")
                    return {
                        "message": "Error in generate new pdf",
                        "success": False,
                        "error": str(e)
                    }

            temp_details = request.env['workflow.templates'].sudo().search([('document_id','=',str(file_data.id))], limit=1) 
            if len(temp_details) != 0:
                workflow_details = request.env['workflow'].sudo().search([('id','=',temp_details.workflow_id.id)], limit=1)
                log_data = {
                    "type": "sign-document",
                    "message": f"Document Signed by {contacts_detail.name} for document ${file_data.name}",
                    "workflow_id": temp_details.workflow_id.id,
                    "node_id": temp_details.node_id,
                    "submission_id": temp_details.submission_id,
                }
                workflow_helper.add_activity_log(log_data)
                if status == temp_details.status:
                    log_data = {
                        "type": "finished-document",
                        "message": f"Workflow completed a template ${file_data.name}",
                        "workflow_id": temp_details.workflow_id.id,
                        "node_id": temp_details.node_id,
                        "submission_id": temp_details.submission_id,
                    }
                    workflow_helper.add_activity_log(log_data)
                    check_next_node.check_next_step(workflow_details, temp_details.node_id, None, temp_details.submission_id)


            create_log_note(file_data.id,f"{contacts_detail.name} signed the document")

            return {
                "message": "You have signed the document",
                "success": True
            }

        except Exception as e:
            _logger.error(f"Error in approve_document: {str(e)}")
            return {
                "message": "An error occurred while processing the request",
                "success": False,
                "error": str(e)
            }