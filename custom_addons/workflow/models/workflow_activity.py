from odoo import models, fields

class WorkflowActivity(models.Model):
    _name = 'workflow.activity'
    _description = 'Workflow Activity'

    workflow_id = fields.Many2one(
        'workflow',
        string='Workflow',
        required=True,
        ondelete='cascade'
    )
    message = fields.Text(
        string='Message',
        required=True
    )
    type = fields.Char(
        string='Type',
        required=True
    )
    node_id = fields.Char(
        string='Node ID',
        default=''
    )
    submission_id = fields.Integer(
        string='Submission ID',
        default=0
    )