from odoo import http
from odoo.http import request, Response
import json
import logging
from odoo.addons.dms_editor.services.signature import SignatureHelper

_logger = logging.getLogger(__name__)
sign = SignatureHelper()


class DeleteUserSignatureController(http.Controller):
    @http.route('/api/user/delete-signature', type='json', auth='user', methods=['POST'], csrf=False)
    def delete_signature(self, **kwargs):
        """
        Delete a user signature.

        :param signature_id: ID of the signature to be deleted.
        :return: JSON response indicating success or failure.
        """
        try:
            signature_id = kwargs.get("signature_id")
            if not signature_id:
                return { "message": "Invalid request. Signature ID is required.", "success": False },

            # Get current user details
            user = request.env.user
            user_id = user.id

            # Find and delete the signature
            signature_record = request.env['user.signature'].sudo().search([('id', '=', signature_id), ('user_id', '=', user_id)], limit=1)
            if not signature_record:
                return { "message": "Signature not found", "success": False }

            # Remove the associated signature files
            sign.remove_old_signature(signature_record.full_signature, signature_record.type)
            sign.remove_old_signature(signature_record.initial_signature, signature_record.type)

            # Delete the signature
            signature_record.unlink()

            # Check if any default signature remains
            remaining_signatures = request.env['user.signature'].sudo().search([('user_id', '=', user_id)], order="id DESC")
            if remaining_signatures and not any(sig.default for sig in remaining_signatures):
                # Set the latest signature as default
                remaining_signatures[0].sudo().write({'default': '1'})

            # Response
            return { "message": "Signature has been deleted successfully.", "success": True }

        except Exception as e:
            _logger.error(f"Error in delete_signature: {str(e)}")
            return { "message": f"An error occurred: {str(e)}", "success": False }
