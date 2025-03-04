from odoo import models, fields, api

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    vehicle_id = fields.Many2one(
        'vehicles',
        string="Vehicle",
        help="Select the vehicle manually"
    )

    vehicle_code = fields.Char(
        string="Vehicle Code",
        compute="_compute_vehicle_code",
        store=True,
        help="Vehicle Code assigned to the selected vehicle"
    )

    @api.depends('vehicle_id')
    def _compute_vehicle_code(self):
        """ Compute vehicle code based on the selected vehicle """
        for rec in self:
            rec.vehicle_code = rec.vehicle_id.code if rec.vehicle_id else ''

    project_id = fields.Many2one(
        'project.project',
        string="Related Project",
        domain="[('id', 'in', available_project_ids)]",
        help="Select the project this attendance belongs to."
    )

    task_id = fields.Many2one(
        'project.task',
        string="Assigned Task",
        domain="[('project_id', '=', project_id), ('user_ids', 'in', user_id)]",
        help="Select the task assigned to the current user."
    )

    available_project_ids = fields.Many2many(
        'project.project',
        compute="_compute_available_projects",
        store=False
    )

    user_id = fields.Many2one(
        'res.users',
        compute="_compute_user_id",
        store=True
    )

    @api.depends('employee_id')
    def _compute_user_id(self):
        """ Automatically fetch the related user for the employee """
        for record in self:
            record.user_id = record.employee_id.user_id if record.employee_id else False

    @api.depends('user_id')
    def _compute_available_projects(self):
        """ Show all projects for all users """
        for record in self:
            record.available_project_ids = self.env['project.project'].search([])

    @api.onchange('project_id')
    def _onchange_project_id(self):
        """ Clear the task selection when the project changes """
        self.task_id = False

    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        """ Calculates worked hours based on check-in/check-out time """
        for rec in self:
            if rec.check_in and rec.check_out:
                delta = rec.check_out - rec.check_in
                rec.worked_hours = delta.total_seconds() / 3600  # Convert seconds to hours
            else:
                rec.worked_hours = 0

    @api.depends('worked_hours')
    def _compute_overtime_hours(self):
        """ Calculates overtime based on standard working hours """
        for rec in self:
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'open')
            ], limit=1)

            standard_hours_per_day = contract.resource_calendar_id.hours_per_day if contract else 8
            rec.overtime_hours = max(0, rec.worked_hours - standard_hours_per_day)
