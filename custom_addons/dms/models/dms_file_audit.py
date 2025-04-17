from odoo import models, fields, api
from datetime import datetime

class FieldChangeLog(models.Model):
    _name = 'dms.file.change.log'
    _description = 'DMS Change Log'

    file_id = fields.Many2one('dms.file', string='File', required=True, ondelete='cascade')
    dms_line_id = fields.Many2one('dms.line', string='ITrack', ondelete='cascade')
    field_name = fields.Char(string='Field Name', required=True)
    old_value = fields.Text(string='Old Value')
    new_value = fields.Text(string='New Value')
    user_id = fields.Many2one('res.users', string='User', required=True)
    change_date = fields.Datetime(string='Change Date', default=fields.Datetime.now)
