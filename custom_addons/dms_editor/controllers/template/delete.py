from odoo import http
from odoo.http import request, Response
import json


class TemplateDeleteRolesController(http.Controller):

    @http.route('/api/template/role/delete', type='http', auth='user', methods=['POST'], csrf=False)
    def delete_template_role(self, **kwargs):
        """
        API to delete a template role and update JSON data accordingly.

        :param id: The ID of the role to be deleted.
        :return: JSON response indicating success or failure.
        """
        try:
            # Get current user
            user = request.env.user
            user_id = user.id

            # Extract role ID
            role_id = kwargs.get('id')
            if not role_id:
                return Response(
                    json.dumps({"success": False, "message": "Invalid Parameters"}),
                    status=400,
                    content_type='application/json'
                )

            # Find and delete the template role
            template_role = request.env['template.roles'].sudo().search([
                ('id', '=', role_id),
                ('user_id', '=', user_id)
            ], limit=1)
            if not template_role:
                return Response(
                    json.dumps({"success": False, "message": "Role not found"}),
                    status=404,
                    content_type='application/json'
                )

            template_id = template_role.template_id
            role_id = template_role.id
            template_role.unlink()

            # Fetch associated document data
            # document_data = request.env['document.data'].sudo().search([
            #     ('document_id', '=', template_id)
            # ])
            # if document_data:
            #     json_data = document_data.read(['json_data'])
            #     new_json = self._filter_obj(json_data, role_id)

            #     # Update the document data
            #     for item in new_json:
            #         document_data_to_update = request.env['document.data'].sudo().search([
            #             ('id', '=', item['id'])
            #         ])
            #         if document_data_to_update:
            #             document_data_to_update.write({'json_data': json.dumps(item['json_data'])})

            return Response(
                json.dumps({"success": True}),
                status=200,
                content_type='application/json'
            )

        except Exception as e:
            return Response(
                json.dumps({"success": False, "message": f"An error occurred: {str(e)}"}),
                status=500,
                content_type='application/json'
            )


    # def _filter_obj(self, data, role_id):
    #     """
    #     Filter and modify JSON data for the specified role ID.
    #     """
    #     pdf_obj = []
    #     for item in data:
    #         item_id = item.get('id')
    #         json_data = item.get('json_data', [])
    #         p_json = []

    #         for obj in json_data:
    #             field_data = obj.get('fieldData', {})
    #             if (
    #                 field_data
    #                 and field_data.get('type')
    #                 and field_data.get('properties', {}).get('role', {}).get('id') == role_id
    #             ):
    #                 if obj.get('type') == "group":
    #                     obj['objects'][0]['fill'] = "rgba(13, 185, 173, 0.7)"
    #                 else:
    #                     obj['fill'] = "rgba(13, 185, 173, 0.7)"
    #                 obj['fieldData']['properties']['role'] = {}
    #             p_json.append(obj)

    #         if p_json:
    #             pdf_obj.append({'id': item_id, 'json_data': p_json})

    #     return pdf_obj if pdf_obj else []