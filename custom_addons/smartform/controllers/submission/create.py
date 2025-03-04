import logging
import json
from odoo import http
from odoo.http import request, Response
from odoo.exceptions import UserError
from datetime import datetime
from odoo.addons.smartform.services.helpers import serialize_record
from odoo.addons.workflow.services.helpers import WorkflowHelper
from odoo.addons.workflow.services.workflow_nodes.check_next_node import CheckNextNode

_logger = logging.getLogger(__name__)

workflow_helper = WorkflowHelper()
check_next_node = CheckNextNode()

class SubmissionCreateController(http.Controller):

    @http.route('/submission/create', type='http', auth='none', methods=['POST'],csrf=False)
    def create_submission(self, **kwargs):
        """
        API to create a submission.

        :param form_id: Form ID (string).
        :param data: Submitted data (JSON).
        :param from: Source of the submission (optional).
        :return: HTTP Response with JSON data indicating success or failure.
        """
        try:
            form_id = kwargs.get('form_id')
            data = kwargs.get('data')
            source = kwargs.get('from')

            if not form_id or not data:
                return Response(
                    status=400,
                    content_type='application/json',
                    response=json.dumps({"success": False, "message": "Missing required parameters."})
                )

            if source:
                # Check if an invite exists for the form and source
                invite_count = request.env['invite'].sudo().search_count([
                    ('form', '=', form_id),
                    ('to_user', '=', source),
                    ('done', '=', '0')
                ])
                if invite_count:
                    # Create submission
                    submission = request.env['submission'].sudo().create({
                        'form_id': form_id,
                        'data': data,
                        'from_user': source
                    })
                    
                    # Update invite as done
                    invite = request.env['invite'].sudo().search([
                        ('form', '=', form_id),
                        ('to_user', '=', source),
                        ('done', '=', '0')
                    ], limit=1)
                    invite.sudo().write({'done': '1'})

                    if invite.from_user.startswith('Workflow:'):
                        workflow_id = int(invite.from_user.split(':')[1])
                        form = request.env['smart.form'].sudo().search([('hash', '=', invite.form)], limit=1)
                        workflow_form = request.env['workflow.forms'].sudo().search([
                            ('workflow_id', '=', workflow_id),
                            ('form_id', '=', form.id)
                        ], limit=1)
                        workflow_form.sudo().write({'status': submission.id})
                        
                        workflow = request.env['workflow'].sudo().search([('id', '=', workflow_id)], limit=1)
                        activity_log = {
                            'type': 'form-completed',
                            'message': f"User {source} submitted form {form.name} #{form.id} for workflow {workflow.name} #{workflow.id}.",
                            'workflow_id': workflow.id,
                            'node_id': workflow_form.node_id
                        }
                        workflow_helper.add_activity_log(activity_log)

                        # Check next step in workflow
                        check_next_node.check_next_step(workflow, workflow_form.node_id, None, submission.id)
                else:
                    return Response(
                        status=200,
                        content_type='application/json',
                        response=json.dumps({
                            "message": "You have already filled this form or this link is no longer available.",
                            "success": False
                        })
                    )
            else:
                # Create a new submission without invite
                submission = request.env['submission'].sudo().create({
                    'form_id': form_id,
                    'data': data,
                })
                form = request.env['smart.form'].sudo().search([('hash', '=', form_id)], limit=1)
                workflow_forms = request.env['workflow.forms'].sudo().search([('form_id', '=', form.id)])

                for workflow_form in workflow_forms:
                    workflow = request.env['workflow'].sudo().search([('id', '=', workflow_form.workflow_id.id)], limit=1)
                    if workflow.status == 'Published':
                        activity_log = {
                            'type': 'create-submission',
                            'message': f"Submission created for form {form.name} #{form.id} in workflow {workflow.name} #{workflow.id}.",
                            'workflow_id': workflow.id,
                            'node_id': workflow_form.node_id,
                            'submission_id': submission.id
                        }
                        workflow_helper.add_activity_log(activity_log)

                        # Check next step in workflow
                        check_next_node.check_next_step(workflow, workflow_form.node_id, None, submission.id)

            return Response(
                status=200,
                content_type='application/json',
                response=json.dumps({
                    "message": "Submission created!",
                    "data": submission.id,
                    "success": True
                })
            )
        except Exception as e:
            _logger.error(f"Error in create_submission: {str(e)}")
            return Response(
                status=500,
                content_type='application/json',
                response=json.dumps({
                    "message": "Error creating submission!",
                    "success": False
                })
            )