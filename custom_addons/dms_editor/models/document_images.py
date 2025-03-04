from odoo import models, fields

class DocumentImages(models.Model):
    _name = 'document.images'
    _description = 'Document Images'

    url = fields.Char(required=True, string='Image URL')
    file_data = fields.Text(string='File Data', help='JSON data for the file')
    document_id = fields.Many2one('dms.file', required=True, string='Document')
    user_id = fields.Many2one('res.users', required=True, string='User')
    thumb_url = fields.Char(required=True, string='Thumbnail URL')
    order_by = fields.Integer(required=True, string='Order')
    is_new = fields.Selection([
        ('1', 'Active'),
        ('0', 'Deactive'),
    ], default='0', required=True, string='Is New')
