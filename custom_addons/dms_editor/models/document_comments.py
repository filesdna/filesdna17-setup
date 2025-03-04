from odoo import models, fields

class DocumentComments(models.Model):
    _name = 'document.comments'
    _description = 'Document Comments'

    user_id = fields.Many2one('res.users', string='User', required=True)
    document_id = fields.Many2one('dms.file', required=True, string='Document')
    page_id = fields.Integer(string='Page')
    position = fields.Json(string='Position')
    message = fields.Text(required=True, string='Message')
    comment_type = fields.Selection(
        [('text', 'Text'), ('voice', 'Voice')],
        default='text',
        required=True,
        string='Type'
    )
    privacy = fields.Selection(
        [('public', 'Public'), ('private', 'Private')],
        default='public',
        required=True,
        string='Privacy'
    )
    duration = fields.Char(string='Duration')
