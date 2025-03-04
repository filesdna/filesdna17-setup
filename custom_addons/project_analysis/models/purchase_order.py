from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    project_id = fields.Many2one(
        'project.project',
        string="Project",
        help="Project linked to this expense."
    )
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """ Assign analytic account to all purchase order lines based on the selected project """
        if self.project_id:
            print(f"DEBUG: Selected Project: {self.project_id.name}")

            if self.project_id.analytic_account_id:
                analytic_account = self.project_id.analytic_account_id
                print(f"DEBUG: Analytic Account ID: {analytic_account.id}")  # Check if the analytic account exists

                for line in self.order_line:
                    print(f"DEBUG: Assigning Analytic Account {analytic_account.id} to Line {line.id}")
                    line.analytic_distribution = {analytic_account.id: 100}
            else:
                print("DEBUG: No Analytic Account Found for the Project!")

    @api.model
    def create(self, vals):
        """ Ensure analytic account is inherited when creating a purchase order """
        purchase_order = super(PurchaseOrder, self).create(vals)

        if purchase_order.origin:
            sale_order = self.env['sale.order'].search([
                '|',
                ('name', '=', purchase_order.origin),
                ('client_order_ref', '=', purchase_order.origin)
            ], limit=1)

            if sale_order and sale_order.project_id:
                purchase_order.project_id = sale_order.project_id
                purchase_order._assign_analytic_account_to_lines()

        return purchase_order

    def write(self, vals):
        """ Ensure analytic account is updated when modifying a purchase order """
        result = super(PurchaseOrder, self).write(vals)
        if 'order_line' in vals or 'project_id' in vals:
            self._assign_analytic_account_to_lines()
        return result

    def _assign_analytic_account_to_lines(self):
        """ Assign analytic account from selected project to all purchase order lines """
        for po in self:
            if po.project_id and po.project_id.analytic_account_id:
                for line in po.order_line:
                    if not line.analytic_distribution:
                        line.analytic_distribution = {po.project_id.analytic_account_id.id: 100.0}
