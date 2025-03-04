from odoo import models, fields

class WorkflowForms(models.Model):
    _name = 'workflow.forms'
    _description = 'Workflow forms'

    workflow_id = fields.Many2one(
        'workflow',
        string='Workflow',
        required=True,
        ondelete='cascade'
    )
    form_id = fields.Integer(
        string='Form ID',
        required=True,
    )
    assign_email = fields.Char(
        string='Assigned Email',
        default=''
    )
    node_id = fields.Char(
        string='Node ID',
        required=True
    )
    status = fields.Char(
        string='Status',
        required=True
    )
    submission_id = fields.Integer(
        string='Submission ID',
        default=0
    )
