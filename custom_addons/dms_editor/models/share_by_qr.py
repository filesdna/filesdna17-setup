from odoo import models, fields, api

class ShareByQr(models.Model):
    _name = 'share.by.qr'
    _description = 'Share by QR'

    # Fields
    document_id = fields.Many2one('dms.file', string='Document', required=True, help="The document being shared")
    share_by = fields.Char(string='Shared By', required=True, help="User who shared the QR code")
    permission = fields.Selection([
        ('view', 'View'),
        ('read', 'Read'),
        ('write', 'Write')
    ], string='Permission', required=True, help="Permission level for the shared QR code")
    hash = fields.Char(string='Hash', required=True, help="Unique hash for the QR code")
    qr_code = fields.Text(string='QR Code', required=True, help="QR code image or data")
    is_expire = fields.Boolean(string='Is Expired', required=True, default=False, help="Whether the QR code is expired")
    expire_time = fields.Char(string='Expire Time', help="Timestamp when the QR code expires")
    day = fields.Integer(string='Days', help="Number of days for which the QR code is valid")
