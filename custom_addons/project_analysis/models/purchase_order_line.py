from odoo import models, fields, api

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'


    analytic_distribution = fields.Json(compute='_compute_name_analytic', store=True)

    @api.depends('order_id.project_id')
    def _compute_name_analytic(self):
        for rec in self:
            if rec.order_id.project_id:
                rec.analytic_distribution = {rec.order_id.project_id.analytic_account_id.id: 100}
                print('test_project_analytic=', rec.order_id.project_id.analytic_account_id.name)
            else:
                rec.analytic_distribution = False
    @api.model
    def create(self, vals):
        """ Assign analytic account automatically when creating a purchase order line """
        line = super(PurchaseOrderLine, self).create(vals)
        line._fill_analytic_distribution()
        return line

    def write(self, vals):
        """ Assign analytic account automatically when modifying a purchase order line """
        result = super(PurchaseOrderLine, self).write(vals)
        if 'product_id' in vals or 'order_id' in vals:
            self._fill_analytic_distribution()
        return result

    @api.onchange('product_id')
    def _onchange_product_id_set_analytic_account(self):
        """ Assign analytic account automatically when a product is selected """
        self._fill_analytic_distribution()

    def _fill_analytic_distribution(self):
        """ Automatically fill analytic distribution when loading purchase order line """
        for line in self:
            if line.order_id and line.order_id.project_id and line.order_id.project_id.analytic_account_id:
                line.analytic_distribution = {line.order_id.project_id.analytic_account_id.id: 100.0}
