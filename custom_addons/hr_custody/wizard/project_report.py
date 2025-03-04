from odoo import _, api, fields, models, tools
from markupsafe import Markup
from datetime import datetime
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError

class AdvanceSearch(models.Model):
    _name = "project.report"

    date_from = fields.Date()
    date_to = fields.Date()
    project_id = fields.Many2one('project.project')

    def action_submit(self):
        print("action_confirm")
        cost = []

        if not self.date_from or not self.date_to:
            raise ValidationError("Add The Date From And The Date To")

        domain = [
            ('create_date', '>=', self.date_from),
            ('create_date', '<=', self.date_to),
        ]

        if self.project_id:
            domain.append(('id', '=', self.project_id.id))
        project = self.env['project.project'].search(domain)

        if project:
            for res in project:
                cost.append({
                    'project_id': res.name,
                    'last_update_id': res.last_update_id.name if res.last_update_id else '',
                    'last_update_status': res.last_update_status,
                })

            return {
                'type': 'ir.actions.report',
                'report_name': 'hr_custody.project_report_template',
                'report_type': 'qweb-html',
                'context': {'active_ids': self.ids},
                'data': {'cost': cost},
            }
        else:
            raise ValidationError("Dont Have Project In This Dates")