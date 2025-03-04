from odoo import models, fields, api

class DMSJsonVersion(models.Model):
    _name = 'dms.json.version'
    _description = 'Dms JSON Version'

    document_id = fields.Many2one('dms.file', required=True, string="Document")
    append_json = fields.Char(required=True, string="Append JSON")
    version = fields.Integer(string="Version")
