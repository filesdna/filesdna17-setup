from odoo import http
from odoo.http import request, Response
import math
import json
import logging

_logger = logging.getLogger(__name__)

class WorkflowGetController(http.Controller):
    @http.route('/api/workflow/index', type='http', auth='user', methods=['GET'], csrf=False)
    def index(self, **kwargs):
        """
        API to get a paginated list of workflows based on filters.
        """
        try:
            user = request.env.user
            user_id = user.id

            # Default filters
            where = [('user_id', '=', user_id)]

            # Apply filters based on input parameters
            name = kwargs.get('name')
            status = kwargs.get('status')
            restart = kwargs.get('restart')
            folder = int(kwargs.get('folder', 0))

            if name:
                where.append(('name', 'ilike', name))
            if status:
                where.append(('status', '=', status))
            if restart is not None:
                where.append(('restart', '=', restart))
            where.append(('folder', '=', folder))

            # Pagination
            per_page = int(kwargs.get('per_page', request.env['ir.config_parameter'].sudo().get_param('default_per_page', 10)))
            page = int(kwargs.get('page', 1))

            # Calculate total records and pagination
            total_records = request.env['workflow'].sudo().search_count(where)
            total_pages = math.ceil(total_records / per_page)
            prev_enable = page > 1
            next_enable = page < total_pages

            start_from = (page - 1) * per_page
            workflows = request.env['workflow'].sudo().search(where, limit=per_page, offset=start_from, order='type ASC, create_date DESC')

            # Prepare response data
            data = [self._serialize_record(workflow) for workflow in workflows]

            response_data = {
                "total_count": total_records,
                "prev_enable": prev_enable if prev_enable else 0,
                "next_enable": next_enable if next_enable else 0,
                "total_pages": total_pages,
                "per_page": per_page,
                "page": page,
                "data": data,
                "success": True,
            }

            # Use Response to return the JSON
            return Response(
                json.dumps(response_data),
                content_type="application/json",
                status=200
            )

        except Exception as e:
            request.env.cr.rollback()
            _logger.error("Error in Workflow API: %s", str(e), exc_info=True)
            error_response = {
                "success": False,
                "message": f"An error occurred: {str(e)}",
            }
            return Response(
                json.dumps(error_response),
                content_type="application/json",
                status=500
            )

    def _serialize_record(self, record):
        """
        Serialize a workflow record for API response.
        """
        return {
            "id": record.id,
            "name": record.name,
            "status": record.status,
            "restart": record.restart,
            "folder": record.folder,
            "type": record.type,
            "current_doc":record.current_doc,
            "current_form":record.current_form,
            "createdat": record.create_date.isoformat(),
            "updatedat": record.write_date.isoformat(),
            "hash_key": record.hash_key,
            "user_id": int(record.user_id),
            "workflow_json": record.workflow_json,
        }
