from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    project_id = fields.Many2one('project.project')


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    analytic_distribution = fields.Json(compute='_compute_name_analytic', store=True)

    @api.depends('order_id.project_id')
    def _compute_name_analytic(self):
        for rec in self:
            if rec.order_id.project_id:
                rec.analytic_distribution = {rec.order_id.project_id.analytic_account_id.id: 100}
                print('test_project_analytic=', rec.order_id.project_id.analytic_account_id.name)
            else:
                rec.analytic_distribution = False
