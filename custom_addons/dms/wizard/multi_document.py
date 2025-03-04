# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

class MultiDocument(models.TransientModel):
    _name = "multi.document"
    _description = "Upload Multiple Documents"

    directory_id = fields.Many2one('dms.directory', "Directory")
    document_ids = fields.Many2many('ir.attachment', 'multi_attachment_rel', 'multi_id',
        'attachment_id', 'Documents', help="Select multiple files to upload.")

    def create_documents(self):
        for rec in self:

            directory = False
            image_1920 = False
            if rec.directory_id:
                directory = rec.directory_id.id          
            for attach in rec.document_ids:
                image = attach.mimetype.split("/")[0]
                if image == 'image':
                    image_1920 = attach.datas

                self.env['dms.file'].create({
                    'name': attach.name,
                    'content': attach.datas,
                    'image_1920': image_1920,
                    'directory_id': directory,
                    })
        return {
                'effect': {
                    'fadeout': 'fast',
                    'message': 'The documents have been successfully uploaded.',
                    'type': 'rainbow_man',
                }
            }