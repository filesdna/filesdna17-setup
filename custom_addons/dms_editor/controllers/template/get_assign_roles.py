from odoo import http
from odoo.http import request, Response
import json


class GetAssignedTemplateRolesController(http.Controller):

    @http.route('/api/template/get-assign-roles', type='http', auth='user', methods=['POST'], csrf=False)
    def get_template_roles(self, **kwargs):
        """
        API to retrieve roles associated with a document's template.

        :param template_id: The ID of the document's template.
        :return: JSON response containing roles or error message.
        """
        try:
            # Get the current user
            user = request.env.user
            user_id = user.id

            # Extract template_id from the input
            document_id = kwargs.get('template_id')
            if not document_id:
                return Response(
                    json.dumps({"success": False, "message": "Missing params."}),
                    status=400,
                    content_type='application/json'
                )

            # Fetch document data for the given template_id and user_id
            # document_data = request.env['document.data'].sudo().search([
            #     ('document_id', '=', document_id),
            #     ('user_id', '=', user_id)
            # ], order='page_id ASC')

            # if not document_data:
            return Response(
                json.dumps({"success": False, "message": "No data found!"}),
                status=404,
                content_type='application/json'
            )

            # Extract unique role IDs from JSON data
            # role_ids = set()
            # for record in document_data:
            #     json_data = json.loads(record.json_data or '[]')
            #     for item in json_data:
            #         field_data = item.get('fieldData', {})
            #         role_id = field_data.get('properties', {}).get('role', {}).get('id')
            #         if role_id and role_id != 0:
            #             role_ids.add(role_id)

            # # Fetch roles matching the extracted role IDs
            # roles = []
            # if role_ids:
            #     roles = request.env['template.roles'].sudo().search_read([
            #         ('id', 'in', list(role_ids)),
            #         ('template_id', '=', document_id)
            #     ], fields=['name', 'color'], order='id DESC')

            # return Response(
            #     json.dumps({"success": True, "data": roles}),
            #     status=200,
            #     content_type='application/json'
            # )

        except Exception as e:
            return Response(
                json.dumps({"success": False, "message": f"An error occurred: {str(e)}"}),
                status=500,
                content_type='application/json'
            )
