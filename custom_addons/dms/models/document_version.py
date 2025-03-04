from odoo import models, fields, api, Command
import hashlib
import base64

class DocumentVersion(models.Model):
    _name = 'document.version'
    _description = 'Document Version'
    _rec_name = 'version_number'

    
    name = fields.Char(string='Name', readonly=True)
    document_id = fields.Many2one('dms.file', string='Document', readonly=True)
    version_number = fields.Integer(string='Version Number', default=1, readonly=True)
    file_data = fields.Binary(string='File Data', readonly=True)
    sha512_hash = fields.Char(string='SHA-512 Hash', readonly=True)
    is_locked = fields.Boolean(string='Locked', related='document_id.is_locked', readonly=True, store=True)
    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Attachment File",
        prefetch=False,
        invisible=True,
        ondelete="cascade")
    attachment_ids = fields.Many2many(comodel_name='ir.attachment', string='File')
    
    
    @api.model
    def create(self, vals):
        last_version = self.search([('document_id', '=', vals.get('document_id'))], order='version_number desc', limit=1)
        if last_version:
            vals['version_number'] = last_version.version_number + 1

        return super(DocumentVersion, self).create(vals)

    def action_delete_record(self):
        self.unlink()

    def download_attachment(self):
        """
        Method to download the attachment.
        """
        self.ensure_one()
        groups = self.document_id.directory_id.complete_group_ids.ids
        self.document_id.has_permission(groups_ids=groups, permission='perm_download')
        attachment_field = self.attachment_ids
        if attachment_field:
            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content/%s?download=true' % (attachment_field[0].id),
                'target': 'current',
            }

    

    

