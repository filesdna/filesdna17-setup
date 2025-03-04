from odoo import models, fields

class Reply(models.Model):
    _name = 'document.reply'
    _description = 'Document Reply'

    user_id = fields.Many2one('res.users', string='User', required=True)
    comment_id = fields.Many2one('document.comments', string='Comment', required=True)
    message = fields.Text(required=True, string='Message')
    reply_type = fields.Selection(
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
