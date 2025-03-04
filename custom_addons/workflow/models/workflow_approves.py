from odoo import models, fields

class WorkflowApproves(models.Model):
    _name = 'workflow.approves'
    _description = 'Workflow Approves'

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
    node_id = fields.Char(
        string='Node ID',
        required=True
    )
    type = fields.Selection(
        [
            ('approval', 'Approval'),
            ('approveSign', 'Approve and Sign'),
            ('teamApproval', 'Team Approval')
        ],
        string='Type',
        required=True
    )
    status = fields.Char(
        string='Status',
        required=True
    )
    outcomes = fields.Char(
        string='Outcomes',
        required=True
    )
    approver = fields.Char(
        string='Approver',
        required=True
    )
    rule = fields.Char(
        string='Rule',
        required=False
    )
    notify = fields.Boolean(
        string='Notify',
        default=False
    )
    require_login = fields.Boolean(
        string='Require Login',
        default=False
    )
    signature = fields.Text(
        string='Signature'
    )
    comment = fields.Char(
        string='Comment',
        required=False
    )
    reassign = fields.Boolean(
        string='Reassign',
        default=False
    )
    require_comment = fields.Boolean(
        string='Require Comment',
        default=False
    )
    escalate = fields.Boolean(
        string='Escalate',
        default=False
    )
    escalate_date = fields.Date(
        string='Escalation Date',
        required=False
    )
    escalate_email = fields.Char(
        string='Escalation Email',
        required=False
    )
    auto_finish = fields.Boolean(
        string='Auto Finish',
        default=False
    )
    auto_finish_date = fields.Date(
        string='Auto Finish Date',
        required=False
    )
    auto_finish_outcome = fields.Char(
        string='Auto Finish Outcome',
        required=False
    )
    submission_id = fields.Integer(
        string='Submission ID',
        default=0
    )
