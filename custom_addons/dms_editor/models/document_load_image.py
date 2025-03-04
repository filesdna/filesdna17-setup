from odoo import models, fields

class DocumentLoadImage(models.Model):
    _name = 'document.load.image'
    _description = 'Document Load Image'

    doc_image_id = fields.Many2one('dms.file', required=True, string='Document Image')
    hash_key = fields.Char(required=True, string='Hash Key')
    image_type = fields.Selection([
        ('F', 'Full'),
        ('T', 'Thumbnail'),
    ], required=True, string='Type')
