from odoo import _, api, fields, models, tools
from markupsafe import Markup
from datetime import datetime
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError


class AdvanceSearch(models.Model):
    _name = "custody.report.search"
    _description = 'Custody Report Search'


    # ----------------------------------------------
    date_from = fields.Date()
    date_to = fields.Date()
    employee_id = fields.Many2many('hr.employee', string="Employees")
    project_id = fields.Many2many('project.project')
    custody_id = fields.Many2many('hr.custody')

    def action_submit(self):
        print("action_confirm")
        cost = []
        domain = []

        if self.project_id:
            domain.append(('project_id', 'in', self.project_id.ids))
        if self.employee_id:
            domain.append(('employee_id', 'in', self.employee_id.ids))

        custody = self.env['hr.custody'].search(domain)

        if custody:
            for res in custody:
                cost.append({
                    'custody_id': res.name,
                    'employee_id': res.employee_id.name,
                    'date_request': res.date_request,
                    'project_id': res.project_id.name,
                    'custody_property_id': ', '.join(res.custody_property_id.mapped('name')),
                    'purpose': res.purpose,
                    'return_date': res.return_date,
                    'notes': res.notes,
                })

            return {
                'type': 'ir.actions.report',
                'report_name': 'hr_custody.custody_report_employee_template',
                'report_type': 'qweb-html',
                'context': {'active_ids': self.ids},
                'data': {'cost': cost},
            }