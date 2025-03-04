import logging
import json
from odoo import http
from odoo.http import request, Response
from odoo.addons.smartform.services.helpers import serialize_record

_logger = logging.getLogger(__name__)

class SmartFormUpdateController(http.Controller):

    @http.route('/smartform/update', type='http', auth='public', methods=['POST'], csrf=False)
    def update_smartform(self, **kwargs):
        try:
            # Extract input parameters
            form_id = int(kwargs.get('id', 0))
            name = kwargs.get('name')
            folder_id = kwargs.get('folder_id')
            is_trash = int(kwargs.get('is_trash', 0))
            user_id = int(kwargs.get('user', 0))

            if not form_id or not user_id:
                response_data = {'message': "Form ID and user ID are required.", 'success': False}
                return Response(json.dumps(response_data), status=400, mimetype='application/json')

            # Fetch the form record using the ID and user_id
            _logger.info(f"form_id:: {form_id}")
            _logger.info(f"user_id:: {user_id}")
            form = request.env['smart.form'].sudo().search([('id', '=', form_id), ('user_id', '=', user_id)], limit=1)
            _logger.info(f"form:: {form}")

            if not form:
                response_data = {'message': "No form found with the given parameters.", 'success': False}
                return Response(json.dumps(response_data), status=404, mimetype='application/json')

            # Validate the name if provided
            if name:
                existing_count = request.env['smart.form'].sudo().search_count([
                    ('user_id', '=', form.user_id.id),
                    ('name', '=', name)
                ])
                if existing_count:
                    response_data = {'message': "This name was already used.", 'success': False}
                    return Response(json.dumps(response_data), status=409, mimetype='application/json')

            # Handle the case where the form is a folder and marked as trash
            if form.type == 'folder' and is_trash:
                # Delete the folder and update child forms
                form.unlink()
                request.env['smart.form'].sudo().search([('folder_id', '=', form_id)]).write({
                    'folder_id': 0,
                    'is_trash': is_trash
                })
                response_data = {'message': "Folder removed!", 'success': True}
                return Response(json.dumps(response_data), status=200, mimetype='application/json')

            if is_trash and form.type == 'form':
                form.write({
                    'is_trash': is_trash
                })
                response_data = { 'message': "Forms removed!", 'data': serialize_record(form.read()[0]), 'success': True }
                return Response(json.dumps(response_data), status=200, mimetype='application/json')

            
            # Update the form with the provided values
            form.write({
                'name': form.name,
                'folder_id': form.folder_id,
            })

            response_data = {
                'message': "Form updated!",
                'data': serialize_record(form.read()[0]),
                'success': True
            }
            return Response(json.dumps(response_data), status=200, mimetype='application/json')

        except Exception as e:
            _logger.error(f"Error updating form: {str(e)}")
            response_data = {'message': f"Error: {str(e)}", 'success': False}
            return Response(json.dumps(response_data), status=500, mimetype='application/json')
