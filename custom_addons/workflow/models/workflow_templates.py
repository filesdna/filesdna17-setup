from odoo import models, fields

class WorkflowTemplates(models.Model):
    _name = 'workflow.templates'
    _description = 'Workflow Templates'

    workflow_id = fields.Many2one(
        'workflow',
        string='Workflow',
        required=True,
        ondelete='cascade'
    )
    template_id = fields.Integer(
        string='Template',
        required=True,
    )
    roles = fields.Char(string='Roles')
    status = fields.Char(
        string='Status',
        default='Completed'
    )
    document_id = fields.Char(string='Document ID')
    is_completed = fields.Boolean(
        string='Is Completed',
        default=True
    )
    node_id = fields.Char(string='Node ID', required=False)
    submission_id = fields.Integer(string='Submission ID')
