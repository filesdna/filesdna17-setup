# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from datetime import timedelta


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    applicant_id = fields.One2many('hr.applicant', 'emp_id', 'Applicant')

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        for employee in employees:
            if employee.applicant_id:
                employee.applicant_id._message_log_with_view(
                    'hr_recruitment.applicant_hired_template',
                    render_values={'applicant': employee.applicant_id}
                )
        return employees
