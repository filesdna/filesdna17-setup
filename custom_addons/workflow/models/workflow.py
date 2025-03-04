from odoo import models, fields

class Workflow(models.Model):
    _name = 'workflow'
    _description = 'Workflow'

    user_id = fields.Char(string='User ID', required=True)
    name = fields.Char(string='Name')
    hash_key = fields.Char(string='Hash Key')
    status = fields.Selection(
        selection=[
            ('Unpublished', 'Unpublished'),
            ('Published', 'Published'),
            ('Completed', 'Completed')
        ],
        string='Status',
        default='Unpublished'
    )
    restart = fields.Selection(
        selection=[
            ("1", 'Yes'),
            ("0", 'No')
        ],
        string='Restart',
        default="0"
    )
    workflow_json = fields.Text(string='Workflow JSON')
    type = fields.Selection(
        selection=[
            ('folder', 'Folder'),
            ('workflow', 'Workflow')
        ],
        string='Type',
        default='workflow'
    )
    folder = fields.Integer(string='Folder', default=0)
    current_form = fields.Integer(string='Current Form')
    current_doc = fields.Integer(string='Current Document')
