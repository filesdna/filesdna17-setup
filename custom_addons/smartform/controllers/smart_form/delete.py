import os
import logging
from odoo import http
from odoo.http import request
from odoo.tools import config

_logger = logging.getLogger(__name__)

server_path = config['server_path']

class SmartFormDeleteController(http.Controller):

    @http.route('/smartform/delete', type='json', auth='public', methods=['POST'])
    def delete_smartform(self, **kwargs):
        try:
            # Extract input parameters
            form_id = kwargs.get('id')
            user_id = kwargs.get('user_id')

            if not form_id and not user_id:
                return {
                    'message': "Either 'id' or 'user_id' is required.",
                    'success': False
                }

            # Handle delete by user_id (Empty trash)
            if user_id:
                forms = request.env['smart.form'].sudo().search([
                    ('user_id', '=', user_id),
                    ('is_trash', '=', True)
                ])

                for form in forms:
                    self._remove_form(form)

                forms.unlink()  # Remove all trashed forms
                return {
                    'message': "Empty Trash!",
                    'success': True
                }

            # Handle delete by form_id
            form = request.env['smart.form'].sudo().search([('id', '=', form_id)], limit=1)
            if not form:
                return {
                    'message': f"No form with id {form_id}.",
                    'success': False
                }

            self._remove_form(form)
            form.unlink()  # Delete the form record

            return {
                'message': "Form deleted!",
                'success': True
            }

        except Exception as e:
            _logger.error(f"Error deleting form: {str(e)}")
            return {'message': f"Error: {str(e)}", 'success': False}

    def _remove_form(self, form):
        """Helper function to delete form files and related submissions."""
        try:
            # Resolve the file path
            file_path = f'{server_path}/smartform/static/src/assets/forms/templates/{form.form_data}.json'
            
            # Delete the form JSON file
            if os.path.exists(file_path):
                os.unlink(file_path)
                _logger.info(f"Deleted form file: {file_path}")
            else:
                _logger.warning(f"File not found: {file_path}")

            #Delete related submissions by form hash
            request.env['submission'].sudo().search([('form_id', '=', form.hash)]).unlink()
            _logger.info(f"Deleted submissions related to form {form.id}")

        except Exception as e:
            _logger.error(f"Error removing form and submissions: {str(e)}")
