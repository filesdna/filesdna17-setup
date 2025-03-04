from odoo import models, fields

class WorkflowEmails(models.Model):
    _name = 'workflow.emails'
    _description = 'Workflow Emails'

    workflow_id = fields.Many2one(
        'workflow',
        string='Workflow',
        required=True,
        ondelete='cascade'
    )
    subject = fields.Char(
        string='Subject',
        required=False
    )
    content = fields.Text(
        string='Content',
        required=False,
        help='JSON content stored as text'
    )
    sender_name = fields.Char(
        string='Sender Name',
        required=False
    )
    sender_email = fields.Char(
        string='Sender Email',
        required=False
    )
    reply_email = fields.Char(
        string='Reply Email',
        required=False
    )
    receiver = fields.Char(
        string='Receiver',
        required=True
    )
    attach = fields.Char(
        string='Attachment',
        required=False
    )
    node_id = fields.Char(
        string='Node ID',
        required=True
    )
    status = fields.Selection(
        [
            ('draft', 'Draft'),
            ('sent', 'Sent'),
            ('failed', 'Failed'),
        ],
        string='Status',
        required=True
    )
    submission_id = fields.Integer(
        string='Submission ID',
        default=0
    )
