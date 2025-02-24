from odoo import models, fields, api

import logging

_logger = logging.getLogger(__name__)


class ProjectProject(models.Model):
    _inherit = 'project.project'

    purchase_order_ids = fields.One2many('purchase.order', 'project_id', string="Purchases")
    attendance_ids = fields.One2many('hr.attendance', 'project_id', string="Attendances")

    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", ondelete='set null')

    employee_ids = fields.Many2many(
        'hr.employee', compute="_compute_employees", store=True, string="Assigned Employees"
    )

    labor_cost_ids = fields.One2many(
        'hr.contract', 'project_id', string="Labor Costs", compute="_compute_labor_costs", store=True
    )

    total_working_hours = fields.Float(string="Total Working Hours", compute="_compute_total_hours", store=True)
    total_overtime_hours = fields.Float(string="Total Overtime Hours", compute="_compute_total_hours", store=True)
    total_salary = fields.Monetary(string="Total Paid Amount", compute="_compute_total_salary", store=True)

    expense_ids = fields.One2many('hr.expense', 'project_id', string="Expenses")
    total_sales = fields.Monetary(string="Total Sales", compute="_compute_totals", store=True,
                                  currency_field="currency_id")
    total_expenses = fields.Monetary(string="Total Expenses", compute="_compute_totals", store=True,
                                     currency_field="currency_id")
    total_purchases = fields.Monetary(string="Total Purchases", compute="_compute_totals", store=True,
                                      currency_field="currency_id")
    profit_loss = fields.Monetary(string="Net Profit/Loss", compute="_compute_totals", store=True,
                                  currency_field="currency_id")

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        string="Currency"

    )

    total_sales = fields.Monetary(
        string="Total Sales",
        compute="_compute_total_sales",
        store=True,
        currency_field="currency_id"
    )
    sale_order_ids = fields.One2many('sale.order', 'project_id')
    hourly_wage = fields.Float(string="Hourly Wage", compute="_compute_hourly_wage", store=False)

    wage = fields.Monetary(string="Wage", currency_field="currency_id")

    @api.depends('wage')
    def _compute_hourly_wage(self):
        for contract in self:
            if contract.resource_calendar_id:
                weekly_hours = sum(
                    attendance.hour_to - attendance.hour_from
                    for attendance in contract.resource_calendar_id.attendance_ids
                )
                total_monthly_hours = weekly_hours * 4
            else:
                total_monthly_hours = 192  # Default assumption

            contract.hourly_wage = round(contract.wage / total_monthly_hours, 2) if total_monthly_hours > 0 else 0

    @api.depends('sale_order_ids.amount_total')
    def _compute_total_sales(self):
        for project in self:
            project.total_sales = sum(project.sale_order_ids.mapped('amount_total'))

    @api.depends('expense_ids.total_amount')
    def _compute_total_expenses(self):
        for project in self:
            project.total_expenses = sum(project.expense_ids.mapped('total_amount'))

    @api.depends('labor_cost_ids')
    def _compute_employees(self):
        """Fetch employees from contracts linked to this project"""
        for project in self:
            project.employee_ids = project.labor_cost_ids.mapped('employee_id')

    @api.depends('attendance_ids.employee_id')
    def _compute_labor_costs(self):
        """ Fetch contracts for employees who attended this project, without requiring tasks. """
        for project in self:
            # Get employees who have attended this project
            employees_with_attendance = self.env['hr.attendance'].search([
                ('project_id', '=', project.id)
            ]).mapped('employee_id')

            # Get active contracts for those employees, regardless of tasks
            contracts = self.env['hr.contract'].search([
                ('employee_id', 'in', employees_with_attendance.ids),
                ('state', '=', 'open')  # Fetch only active contracts
            ])

            # Assign the retrieved contracts to the project
            project.labor_cost_ids = contracts

            # Debugging logs
            _logger.info(f"🔍 Labor Cost Computation for Project: {project.name}")
            _logger.info(f"📌 Employees Found: {employees_with_attendance.mapped('name')}")
            _logger.info(f"💰 Contracts Retrieved: {contracts.mapped('employee_id.name')}")

    @api.depends('labor_cost_ids.employee_id', 'attendance_ids.check_in', 'attendance_ids.check_out')
    def _compute_total_hours(self):
        """ Compute total working and overtime hours for employees who attended this project without date constraints """
        for project in self:
            total_hours = 0
            total_overtime = 0

            _logger.info(f"=== COMPUTING HOURS FOR PROJECT: {project.name} (ID: {project.id}) ===")

            # ✅ Fetch all attendances linked to this project
            attendances = self.env['hr.attendance'].search([
                ('employee_id', 'in', project.labor_cost_ids.mapped('employee_id').ids),
                ('project_id', '=', project.id)  # ✅ Ensure the attendance is linked to this project
            ])

            _logger.info(f"✅ Found {len(attendances)} attendances for project {project.name}")

            for attendance in attendances:
                contract = self.env['hr.contract'].search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('state', '=', 'open')
                ], limit=1)

                _logger.info(
                    f"✅ Attendance - Employee: {attendance.employee_id.name}, Hours: {attendance.worked_hours}")

                if contract:
                    standard_hours_per_day = contract.resource_calendar_id.hours_per_day or 8
                    work_hours = attendance.worked_hours
                    overtime = max(0, work_hours - standard_hours_per_day)

                    _logger.info(f"🔹 Computed Work Hours: {work_hours}, Overtime: {overtime}")

                    total_hours += work_hours
                    total_overtime += overtime

            _logger.info(f"💡 FINAL COMPUTED HOURS - Total: {total_hours}, Overtime: {total_overtime}")

            project.total_working_hours = total_hours
            project.total_overtime_hours = total_overtime

    @api.depends('total_working_hours', 'total_overtime_hours', 'labor_cost_ids')
    def _compute_total_salary(self):
        for project in self:
            total_salary = 0
            print(f"\n=== COMPUTING SALARY FOR PROJECT: {project.name} (ID: {project.id}) ===")
            print(
                f"📊 Total Working Hours: {project.total_working_hours}, Total Overtime: {project.total_overtime_hours}")

            for contract in project.labor_cost_ids:
                print(f"🔍 Contract: {contract.id}, Employee: {contract.employee_id.name}")

                if contract.wage:
                    print(f"\n🔍 Contract: {contract.id}, Employee: {contract.employee_id.name}")
                    # ✅ Fix: Get total working hours per week
                    if contract.resource_calendar_id:
                        weekly_hours = sum(
                            attendance.hour_to - attendance.hour_from
                            for attendance in contract.resource_calendar_id.attendance_ids
                        )
                        total_monthly_hours = weekly_hours * 4  # Approximate monthly working hours
                    else:
                        total_monthly_hours = 192  # Default value if no calendar is assigned

                    wage_per_hour = contract.wage / total_monthly_hours if total_monthly_hours > 0 else 0

                    print(f"📆 Calculated Monthly Hours: {total_monthly_hours}")

                    # Compute wage per hour dynamically
                    wage_per_hour = contract.wage / total_monthly_hours if total_monthly_hours > 0 else 0
                    print(f"💰 Monthly Salary: {contract.wage}")
                    print(f"💰 Wage Per Hour: {wage_per_hour}")

                    overtime_rate = 1.5  # Overtime rate: 1.5x

                    # Compute total salary based on normal hours & overtime
                    employee_salary = (
                            (project.total_working_hours * wage_per_hour) +
                            (project.total_overtime_hours * wage_per_hour * overtime_rate)
                    )
                    print(f"✅ Computed Salary for {contract.employee_id.name}: {employee_salary}")

                    total_salary += employee_salary
                else:
                    print(f"⚠️ WARNING: No resource calendar found for {contract.employee_id.name}")

        project.total_salary = total_salary
        print(f"✅ FINAL COMPUTED SALARY: {project.total_salary}\n")

    def action_recompute_hours_salary(self):
        """ Manually trigger the recomputation of total hours and salary """
        for project in self:
            project._compute_labor_costs()  # ✅ Ensure labor costs are updated first
            project._compute_total_hours()
            project._compute_total_salary()

    @api.depends('sale_order_ids.amount_total', 'expense_ids.total_amount', 'purchase_order_ids.amount_total',
                 'total_salary')
    def _compute_totals(self):
        for project in self:
            total_sales = sum(project.sale_order_ids.mapped('amount_total'))
            total_expenses = sum(project.expense_ids.mapped('total_amount'))
            total_purchases = sum(project.purchase_order_ids.mapped('amount_total'))
            total_labor_cost = project.total_salary

            project.total_sales = total_sales
            project.total_expenses = total_expenses
            project.total_purchases = total_purchases

            # Calculate Profit/Loss
            project.profit_loss = total_sales - (total_expenses + total_purchases + total_labor_cost)

    @api.model
    def create(self, vals):
        """ Automatically create an analytic account when creating a project """
        project = super(ProjectProject, self).create(vals)
        analytic_account = self.env['account.analytic.account'].create({
            'name': vals.get('name'),
            'plan_id': 1,  # Make sure this plan_id exists in your system
        })
        project.analytic_account_id = analytic_account.id
        return project

    def name_get(self):
        """ Force correct naming for projects """
        result = []
        for project in self:
            result.append((project.id, project.name))
        return result
