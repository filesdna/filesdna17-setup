from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, time
from odoo.exceptions import ValidationError


class DmsLinkFilesWizard(models.TransientModel):
    _name = 'dms.link.files.wizard'
    _description = 'Link Files Wizard'

    file_id = fields.Many2one('dms.file')
    reference_file = fields.Char(compute='_compute_file_id')
    date_from = fields.Date()
    date_to = fields.Date()
    in_out = fields.Selection([('in', 'IN'), ('out', 'OUT')], 'In/Out')
    confidentiality_level_id = fields.Many2one('dms.type', string='Confidentiality Level')
    degree_of_secrecy = fields.Many2one('dms.degree.of.secrecy', string='Degree of secrecy')

    @api.onchange('file_id')
    def _compute_file_id(self):
        self.reference_file = self.file_id.reference

    def action_search(self):
        if not self.date_from or not self.date_to:
            raise ValidationError("Add The Date From And The Date To")
        domain = []

        if self.date_from and self.date_to:
            domain.append(('create_date', '>=', self.date_from))
            domain.append(('create_date', '<=', self.date_to))

        if self.in_out:
            domain.append(('in_out', '=', self.in_out))
        if self.confidentiality_level_id:
            domain.append(('confidentiality_level_id', '=', self.confidentiality_level_id.id))
        if self.degree_of_secrecy:
            domain.append(('degree_of_secrecy', '=', self.degree_of_secrecy.id))
        return {
            'type': 'ir.actions.act_window',
            'name': 'Search DMS Files',
            'res_model': 'dms.file',
            'view_mode': 'tree',
            'view_id': self.env.ref('dms.view_dms_file_search').id,
            'domain': domain,
            'target': 'new',
            'context': dict(self.env.context, create=False),
        }

