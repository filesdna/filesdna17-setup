from odoo import models, fields, api
from datetime import timedelta

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    month_working_days = fields.Float(
        string='Working Days (Month)',
        compute='_compute_month_working_days',
        store=True
        
    )

    @api.depends('date_from', 'date_to')
    def _compute_month_working_days(self):
        for payslip in self:
            if payslip.date_from and payslip.date_to:
                current_date = payslip.date_from
                total_working_days = 0
                while current_date <= payslip.date_to:
                    # weekday() => Monday=0, Tuesday=1, ..., Saturday=5, Sunday=6
                    # We skip only Saturday (weekday() == 5)
                    if current_date.weekday() != 5:
                        total_working_days += 1
                    current_date += timedelta(days=1)

                payslip.month_working_days = total_working_days
            else:
                payslip.month_working_days = 0
