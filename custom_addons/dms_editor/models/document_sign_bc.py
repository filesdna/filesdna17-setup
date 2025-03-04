from odoo import models, fields

class DocumentSignBlockchain(models.Model):
    _name = 'document.sign.bc'
    _description = 'Document Sign Blockchain'

    user_id = fields.Char(string='User ID', required=True)
    document_id = fields.Integer(string='Document ID', required=True)
    hash_value = fields.Char(string='Hash Value')
    bc_document = fields.Text(string='Blockchain Document')
    bc_signature = fields.Char(string='Blockchain Signature')
    email = fields.Char(string='Email')
    owner_id = fields.Char(string='Owner ID', required=True)
    date = fields.Datetime(string='Date')
