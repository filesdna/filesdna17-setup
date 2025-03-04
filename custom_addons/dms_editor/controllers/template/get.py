from odoo import http
from odoo.http import request, Response
import json


class GetTemplateRolesController(http.Controller):

    @http.route('/api/template/roles', type='http', auth='user', methods=['GET'], csrf=False)
    def search_template_roles(self, **kwargs):
        """
        API to search for roles associated with a document's template.

        :param template_id: The ID of the document's template.
        :param name: The (optional) name or part of the name to filter roles.
        :return: JSON response containing the roles or an error message.
        """
        try:
            # Get the current user
            user = request.env.user
            user_id = user.id

            # Extract inputs
            template_id = kwargs.get('template_id')
            name = kwargs.get('name')

            if not template_id:
                return Response(
                    json.dumps({"success": False, "message": "Missing params."}),
                    status=400,
                    content_type='application/json'
                )

            # Build the search domain
            domain = [('template_id', '=', template_id)]
            if name:
                domain.append(('name', 'ilike', name))

            # Query the template roles
            roles = request.env['template.roles'].sudo().search(domain, order='id DESC')

            serialized_roles = [
                {
                    'id': role.id,
                    'template_id': role.template_id if role.template_id else None,
                    'name': role.name,
                    'color': role.color,
                }
                for role in roles
            ]

            return Response(
                json.dumps({"success": True, "data": serialized_roles}),
                status=200,
                content_type='application/json'
            )

        except Exception as e:
            return Response(
                json.dumps({"success": False, "message": f"An error occurred: {str(e)}"}),
                status=500,
                content_type='application/json'
            )
