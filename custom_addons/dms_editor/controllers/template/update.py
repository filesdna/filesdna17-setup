from odoo import http
from odoo.http import request, Response
import json


class TemplateUpdateRolesController(http.Controller):

    @http.route('/api/template/role/update', type='http', auth='user', methods=['POST'], csrf=False)
    def update_template_role(self, **kwargs):
        """
        API to update a role associated with a template.

        :param id: The ID of the role to update.
        :param name: The new name for the role.
        :param template_id: The ID of the associated template.
        :return: JSON response indicating success or failure.
        """
        try:
            # Extract inputs
            role_id = int(kwargs.get('id'))
            name = kwargs.get('name')
            template_id = int(kwargs.get('template_id'))

            # Validate required inputs
            if not role_id or not name or not template_id:
                return Response(
                    json.dumps({"success": False, "message": "Invalid Parameters"}),
                    status=400,
                    content_type='application/json'
                )

            # Check for duplicate role names
            existing_roles = request.env['template.roles'].sudo().search([
                ('name', '=', name),
                ('id', '!=', role_id),
                ('template_id', '=', template_id)
            ], limit=1)

            if existing_roles:
                return Response(
                    json.dumps({"success": False, "message": "This role already exists"}),
                    status=400,
                    content_type='application/json'
                )

            # Update the role
            role = request.env['template.roles'].sudo().browse(role_id)
            if role and role.template_id == template_id:
                role.write({'name': name})
                return Response(
                    json.dumps({"success": True, "data": {'id': role.id, 'name': role.name, 'template_id': role.template_id}}),
                    status=200,
                    content_type='application/json'
                )
            else:
                return Response(
                    json.dumps({"success": False, "message": "Role not found or unauthorized"}),
                    status=404,
                    content_type='application/json'
                )

        except Exception as e:
            return Response(
                json.dumps({"success": False, "message": f"An error occurred: {str(e)}"}),
                status=500,
                content_type='application/json'
            )
