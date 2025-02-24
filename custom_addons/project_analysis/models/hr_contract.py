from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class HrContract(models.Model):
    _inherit = 'hr.contract'

    project_id = fields.Many2one(
        'project.project', compute="_compute_project", store=True, string="Project"
    )

    task_id = fields.Many2one('project.task', string="Assigned Task",
                              help="Task assigned to the employee for this contract.")
    weekly_hours = fields.Float(string="Weekly Working Hours", compute="_compute_weekly_hours", store=True)
    hourly_wage = fields.Monetary(string="Hourly Wage (/hr)", compute="_compute_hourly_wage", store=True,
                                  currency_field='currency_id')
    weekly_wage = fields.Monetary(string="Weekly Wage (/week)", compute="_compute_weekly_wage", store=True,
                                  currency_field='currency_id')  # ✅ Add this
    total_working_hours = fields.Float(string="Total Working Hours", compute="_compute_total_working_hours", store=True)
    total_overtime_hours = fields.Float(string="Total Overtime Hours", compute="_compute_total_overtime_hours",
                                        store=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, string="Currency")

    @api.depends('resource_calendar_id')
    def _compute_weekly_hours(self):
        """ Compute Weekly Working Hours from the Resource Calendar """
        for contract in self:
            if contract.resource_calendar_id:
                total_weekly_hours = sum(
                    attendance.hour_to - attendance.hour_from
                    for attendance in contract.resource_calendar_id.attendance_ids
                )
                contract.weekly_hours = total_weekly_hours
                _logger.info(
                    f"🔍 DEBUG: Contract: {contract.id} | Employee: {contract.employee_id.name} | Computed Weekly Hours: {contract.weekly_hours}")
            else:
                contract.weekly_hours = 48  # Default if no schedule
                _logger.warning(
                    f"⚠️ WARNING: No resource calendar found for {contract.employee_id.name}, defaulting to 48 hours.")

    @api.depends('wage', 'weekly_hours')
    def _compute_hourly_wage(self):
        """ Compute hourly wage based on weekly working hours """
        for contract in self:
            if contract.weekly_hours > 0:
                total_monthly_hours = contract.weekly_hours * 4.33  # Approximate month weeks
                contract.hourly_wage = contract.wage / total_monthly_hours if total_monthly_hours > 0 else 0.0
                _logger.info(
                    f"🔍 DEBUG: Contract: {contract.id} | Employee: {contract.employee_id.name} | Hourly Wage: {contract.hourly_wage}")
            else:
                contract.hourly_wage = 0.0

    @api.depends('wage')
    def _compute_weekly_wage(self):
        """ Compute weekly wage based on monthly salary """
        for contract in self:
            contract.weekly_wage = contract.wage / 4.33 if contract.wage else 0.0
            _logger.info(
                f"🔍 DEBUG: Contract: {contract.id} | Employee: {contract.employee_id.name} | Weekly Wage: {contract.weekly_wage}")

    @api.depends('employee_id', 'employee_id.attendance_ids')
    def _compute_total_working_hours(self):
        """ Compute Total Working Hours from Attendance Records """
        for contract in self:
            total_hours = sum(contract.employee_id.attendance_ids.mapped('worked_hours'))
            contract.total_working_hours = total_hours
            _logger.info(
                f"🔍 DEBUG: Contract: {contract.id} | Employee: {contract.employee_id.name} | Total Working Hours: {total_hours}")

    @api.depends('total_working_hours')
    def _compute_total_overtime_hours(self):
        """ Compute Overtime Hours based on contract working hours """
        for contract in self:
            standard_weekly_hours = contract.weekly_hours if contract.weekly_hours else 48  # Default to 48
            monthly_standard_hours = standard_weekly_hours * 4.33  # Monthly estimate

            overtime_hours = max(0, contract.total_working_hours - monthly_standard_hours)
            contract.total_overtime_hours = overtime_hours
            _logger.info(
                f"🔍 DEBUG: Contract: {contract.id} | Employee: {contract.employee_id.name} | Total Overtime Hours: {overtime_hours}")

    @api.depends('employee_id')
    def _compute_project(self):
        """ Automatically assign contract to a project based on employee assignment """
        for contract in self:
            project = self.env['project.project'].search([
                ('employee_ids', 'in', contract.employee_id.id)
            ], limit=1)
            contract.project_id = project.id if project else False
