import logging
from odoo import http
from odoo.http import request, Response
import json
from datetime import datetime

_logger = logging.getLogger(__name__)

class SmartFormController(http.Controller):

    @http.route('/smartform/index', type='http', auth='public', methods=['GET'])
    def index_smartform(self, **kwargs):
        try:
            # Extract inputs from query parameters
            user_id = request.params.get('user_id')
            is_trash = int(request.params.get('is_trash', 0))
            folder_id = int(request.params.get('folder_id', 0))
            name = request.params.get('name', '')
            date = request.params.get('date', '')

            if not user_id:
                raise ValueError("User ID is required.")

            # Fetch the user and their company name
            user = request.env['res.users'].sudo().browse(int(user_id))

            if not user.exists():
                return Response(
                    json.dumps({'message': 'User not found.', 'success': False}),
                    content_type='application/json',
                    status=404,
                )

            # Fetch all users from the same company
            users = request.env['res.users'].sudo().search([('company_id', '=', user.company_id.id)])
            user_ids = users.mapped('id')

            # Build the search domain
            domain = [('user_id', 'in', user_ids), ('is_trash', '=', is_trash)]

            if not is_trash:
                domain.append(('folder_id', '=', folder_id))

            if name:
                domain.append(('name', 'ilike', name))

            if date:
                domain.append(('create_date', '=', date))

            # Fetch smart forms matching the domain and sort them
            forms = request.env['smart.form'].sudo().search(domain, order='type ASC, id DESC')

            # Add submission count to each form
            result = []
            for form in forms:
                submission_count = request.env['submission'].sudo().search_count([('form_id', '=', form.hash)])
                form_data = form.read()[0]
                form_data['submissions'] = submission_count
                result.append(self._serialize_datetime(form_data))

            # Handle parent folder logic if folder_id is provided
            parent_id = 0
            parent_folder = []
            if folder_id:
                parent_folder = self._get_parent_folders(folder_id)
                parent_id = parent_folder[0].get('folder_id', 0) if parent_folder else 0

            response_data = {
                'message': "User form read!",
                'data': result,
                'success': True,
                'parent_id': parent_id,
                'parentFolder': sorted(parent_folder, key=lambda x: x['id'])
            }

            # Return the response as valid JSON
            return Response(
                json.dumps(response_data, default=self._json_default),
                content_type='application/json',
                status=200,
            )

        except Exception as e:
            _logger.error(f"Error: {str(e)}")
            return Response(
                json.dumps({'message': f"Error: {str(e)}", 'success': False}),
                content_type='application/json',
                status=500,
            )

    def _get_parent_folders(self, folder_id):
        """Helper function to get the hierarchy of parent folders."""
        parent_folders = []
        while folder_id != 0:
            folder = request.env['smart.form'].sudo().search([('id', '=', folder_id)], limit=1)
            if not folder:
                break
            parent_folders.append({
                'id': folder.id,
                'name': folder.name,
                'folder_id': folder.folder_id
            })
            folder_id = folder.folder_id
        return parent_folders

    def _json_default(self, obj):
        """Custom JSON serializer for datetime objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()  # Convert to 'YYYY-MM-DDTHH:MM:SS' format
        raise TypeError(f"Type {type(obj)} not serializable")

    def _serialize_datetime(self, data):
        """Recursively convert datetime objects in dictionaries to string format."""
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data
