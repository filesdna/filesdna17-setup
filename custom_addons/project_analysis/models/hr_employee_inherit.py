from odoo import models, fields


class HREmployee(models.Model):
    _inherit = "hr.employee"

    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        help="Analytic account linked to this employee."
    )
    project_id = fields.Many2one(
        'project.project', store=True, string="Project"
    )
