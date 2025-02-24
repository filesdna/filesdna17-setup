from odoo import models, fields, api


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    project_id = fields.Many2one(
        'project.project',
        string="Project",
        domain="[('id', 'in', available_project_ids)]",
        help="Select a project where you have assigned tasks."
    )

    available_project_ids = fields.Many2many(
        'project.project',
        compute="_compute_available_projects",
        store=False
    )

    @api.depends('employee_id')
    def _compute_available_projects(self):
        """ Show all projects for all users """
        for record in self:
            record.available_project_ids = self.env['project.project'].search([])