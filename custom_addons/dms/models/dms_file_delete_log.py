from odoo import api, fields, models

class DMSFileDeleteLog(models.Model):
    _name = 'dms.file.delete.log'
    _description = 'Log of Deleted Files'

    name = fields.Char(string='File Name')
    extension = fields.Char(string='Extension')
    delete_date = fields.Datetime(string='Delete Date', default=fields.Datetime.now)
    deleted_by = fields.Many2one('res.users', string='Deleted By')
    created_on = fields.Datetime('Date of creation')
