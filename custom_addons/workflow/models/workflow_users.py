from odoo import models, fields

class WorkflowUsers(models.Model):
    _name = 'workflow.users'
    _description = 'Workflow Users'

    workflow_id = fields.Many2one(
        'workflow', 
        string='Workflow', 
        required=True, 
        ondelete='cascade'
    )
    user_id = fields.Char(string='User ID', required=True)
    is_working = fields.Selection(
        selection=[
            ("1", 'Yes'),
            ("0", 'No')
        ],
        string='Is Working',
        default="0"
    )
