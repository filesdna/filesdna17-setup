from odoo import http
from odoo.http import request, Response
import json


class TemplateAddRolesController(http.Controller):

    @http.route('/api/template/role/add', type='http', auth='user', methods=['POST'], csrf=False)
    def create_template_role(self, **kwargs):
        """
        Create a new template role if it doesn't already exist for the user.
        """
        try:
            # Get current user ID
            user = request.env.user
            user_id = user.id

            # Extract inputs
            template_id = kwargs.get('template_id')
            name = kwargs.get('name')
            color = kwargs.get('color')

            # Validate inputs
            if not template_id or not name or not color:
                return Response(
                    json.dumps({
                        "success": False,
                        "message": "Missing params.",
                    }),
                    status=400,
                    content_type='application/json'
                )

            # Check if role already exists
            existing_roles = request.env['template.roles'].sudo().search([
                ('user_id', '=', user_id),
                ('name', '=', name),
                ('template_id', '=', template_id)
            ])
            if existing_roles:
                return Response(
                    json.dumps({
                        "success": False,
                        "message": "This role already exists."
                    }),
                    status=400,
                    content_type='application/json'
                )

            # Create a new role
            new_role = request.env['template.roles'].sudo().create({
                'user_id': user_id,
                'name': name,
                'color': color,
                'template_id': template_id,
            })

            return Response(
                json.dumps({
                    "success": True,
                    "data": {
                        "id": new_role.id,
                        "name": new_role.name,
                        "color": new_role.color,
                        "template_id": new_role.template_id
                    }
                }),
                status=200,
                content_type='application/json'
            )

        except Exception as e:
            return Response(
                json.dumps({
                    "success": False,
                    "message": f"An error occurred: {str(e)}"
                }),
                status=500,
                content_type='application/json'
            )
