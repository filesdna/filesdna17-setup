# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _


class DocumentType(models.Model):
    """Document Type"""
    _name = 'document.type'
    _description = __doc__
    _rec_name = 'document_type'

    document_type = fields.Char(string="Document", required=True)


class CaseMatterDocument(models.Model):
    """Case Matter Document"""
    _name = 'case.matter.document'
    _description = __doc__
    _rec_name = 'case_matter_id'

    case_matter_id = fields.Many2one('case.matter', string="Case")
    file_name = fields.Char(string="filename")
    avatar = fields.Binary(string="Document", required=True)
    document_type_id = fields.Many2one('document.type', string="Document Type", required=True)
