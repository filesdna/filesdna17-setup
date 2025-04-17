from odoo import models, fields, api
import logging
import secrets
import string
from datetime import datetime
from odoo.http import request, Response
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)

class DocumentSignService:

    def save_json_data(self, json_array, user_data, check_file):
        """
        Save JSON data and process signing users.
        """
        try:
            if not json_array:
                return True

            unique_emails = {item['signer']['email'] for item in json_array if item.get('signer')}
            
            if check_file.document_status != "Pending Owner":
                try:
                    self.delete_signer(check_file.id)
                except Exception as e:
                    _logger.error(f"Error deleting signer: {str(e)}")
                    raise UserError("Error deleting signer")

            for email in unique_emails:
                # Process individual emails
                partner = request.env['res.users'].sudo().search([('login', '=', email)], limit=1)

                self.add_document_sign_user(
                    document_id=check_file.id,
                    email=email,
                    order_by=0,
                    is_guest=not partner,
                    sent_by=user_data['name'],
                    status='Draft',
                    sent_by_email=user_data['email'],
                    security_type='',
                    sms_content={},
                    user_data=user_data,
                    file_data=check_file,
                )
                # if partner:
                #     self.send_update_event(partner.id)
            return True

        except Exception as e:
            _logger.error(f"Error in save_json_data: {str(e)}")
            raise UserError(f"Error saving JSON data: {str(e)}")

    def delete_signer(self, document_id):
        """
        Delete signers for a specific document.
        """
        request.env['document.sign'].sudo().search([('document_id', '=', document_id)]).unlink()
        return True

    def add_document_sign_user(self, document_id, email, order_by, is_guest, sent_by, status, sent_by_email, security_type, sms_content, user_data=None, file_data=None):
        """
        Add signing users to the document.
        """
        DocumentSign = request.env['document.sign'].sudo()
        existing_signer = DocumentSign.search([('document_id', '=', document_id), ('email', '=', email)], limit=1)

        if existing_signer:
            existing_signer.write({
                'order_by': order_by,
                'status': status,
                'security_type': security_type,
                'number_fill_by': 'recipient' if security_type == 'sms_security' and not sms_content.get('number_fill_by') else sms_content.get('number_fill_by'),
                'sms_country': sms_content.get('sms_country'),
                'sms_phone_no': sms_content.get('sms_phone_no'),
            })
            return existing_signer

        # Add new signer
        new_signer = DocumentSign.create({
            'document_id': document_id,
            'email': email.lower(),
            'user_hash': self._generate_random_hash(40),
            'order_by': order_by,
            'is_guest': is_guest,
            'status': status,
            'sent_by': sent_by,
            'sent_by_email': sent_by_email,
            'date': fields.Date.today(),
            'delegate_email': self.is_delegate_user(email.lower()),
            'security_type': security_type,
            'sms_country': sms_content.get('sms_country'),
            'sms_phone_no': sms_content.get('sms_phone_no'),
        })
        return new_signer

    def is_delegate_user(self, email):
        """
        Check if the email belongs to a delegate user.
        """
        delegate = request.env['sign.delegate'].sudo().search([('email', '=', email)], limit=1)
        return delegate.delegate_email if delegate else None

    # def send_update_event(self, user_id):
    #     """
    #     Trigger an event to notify a user about sign request updates.
    #     """
    #     # Placeholder for sending a notification event
    #     _logger.info(f"Update sign request event sent to user_id: {user_id}")


    def _generate_random_hash(self, length=40):
        """
        Generate a random alphanumeric hash of the specified length.
        """
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))