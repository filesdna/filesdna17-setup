from odoo import models, fields, api
from odoo.exceptions import UserError


class DmsFileLine(models.Model):
    _name = "dms.file.line"
    _description = "Linked File Line"

    file_id = fields.Many2one('dms.file', string="Linked File", required=True, ondelete="cascade")
    parent_file_id = fields.Many2one('dms.file', string="Parent File", ondelete="cascade", required=True)
    directory_id = fields.Many2one('dms.directory', string="Directory", related='file_id.directory_id', store=True)
    full_directory_path = fields.Char(string="Full Directory Path", compute='_compute_full_directory_path', store=True)
    notes = fields.Text(string="Notes")
    content = fields.Binary(related="file_id.content", string="Content", readonly=True)
    mimetype = fields.Char(related="file_id.mimetype", string="MIME Type", readonly=True)
    extension = fields.Char(related="file_id.extension", string="Extension", readonly=True)
    attachment_id = fields.Many2many('ir.attachment', string="Attachment")

    @api.model
    def create(self, vals):
        record = super(DmsFileLine, self).create(vals)
        if 'file_id' in vals:
            # Automatically attach the linked file
            file = self.env['dms.file'].browse(vals['file_id'])
            if file.content:
                attachment = self.env['ir.attachment'].create({
                    'name': file.name,
                    'datas': file.content,
                    'mimetype': file.mimetype,
                    'res_model': 'dms.linked.files',
                    'res_id': record.id,
                })
                record.attachment_id = [(4, attachment.id)]
        return record

    @api.depends('directory_id')
    def _compute_full_directory_path(self):
        for record in self:
            if record.directory_id:
                path_parts = []
                current_dir = record.directory_id
                while current_dir:
                    path_parts.insert(0, current_dir.name)
                    current_dir = current_dir.parent_id
                record.full_directory_path = " / ".join(path_parts)
            else:
                record.full_directory_path = ""

    def action_preview(self):
        """Generates a preview action for the linked file."""
        self.ensure_one()
        if not self.file_id or not self.file_id.content:
            raise UserError("No content available for preview.")
        if self.file_id.mimetype == "application/pdf":
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{self.file_id.id}/content/{self.file_id.name}',
                'target': 'new',
            }
        elif self.file_id.mimetype.startswith("image/"):
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{self.file_id.id}/content/{self.file_id.name}',
                'target': 'new',
            }
        else:
            raise UserError("Preview is not available for this file type.")
