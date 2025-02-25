from odoo import models, fields, api
import logging

from zeep.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class BSSaleOrder(models.Model):
    _inherit = 'sale.order'

    state = fields.Selection([
        ('estimate', 'Estimation'),
        ('toapprove', 'To Approve'),
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Job Order'),
        ('accounts', 'Accounts'),
        ('cancel', 'Cancelled'),  # Only used when an estimation is declined
    ], string='Status', readonly=True, copy=False, index=True, default='estimate')

    due_amount = fields.Monetary(
        string="Due Amount",
        compute="_compute_due_amount",
        store=True
    )

    has_due = fields.Boolean(
        string="Has Due",
        compute="_compute_has_due",
        store=True
    )

    approver_id = fields.Many2one(
        'res.users',
        string='Approver',
        compute='_compute_approver_id',
        store=True,
        readonly=False
    )

    is_warning = fields.Boolean(
        string="Is Warning",
        compute="_compute_is_warning",
        store=True
    )

    decline_reason = fields.Text(string="Decline Reason", help="Reason for declining the estimation.")
    po_count = fields.Integer(
        string="Purchase Order Count",
        compute="_compute_po_count",
        store=True
    )

    project_id = fields.Many2one('project.project', string="Related Project")
    invoice_status = fields.Selection([
        ('upselling', 'Upselling Opportunity'),
        ('no', 'No Invoice'),
        ('to invoice', 'To Invoice'),
        ('invoiced', 'Fully Invoiced'),
        ('partially invoiced', 'Partially Invoiced'),
    ], string='Invoice Status', compute='_compute_invoice_status', store=True, readonly=True)

    @api.depends('order_line.invoice_status')
    def _compute_invoice_status(self):
        """Compute the invoice status based on invoiced amounts."""
        for order in self:
            if all(line.invoice_status == 'invoiced' for line in order.order_line):
                order.invoice_status = 'invoiced'  # ✅ Fully Invoiced
            elif any(line.invoice_status == 'to invoice' for line in order.order_line):
                order.invoice_status = 'to invoice'  # ✅ Some items need to be invoiced
            elif any(line.invoice_status == 'partially invoiced' for line in order.order_line):
                order.invoice_status = 'partially invoiced'  # ✅ Partial Invoice
            else:
                order.invoice_status = 'no'  # ✅ No invoice needed

    def action_invoice_create(self):
        """Create invoice and update invoice status"""
        invoices = super(BSSaleOrder, self).action_invoice_create()
        for order in self:
            order.order_line._compute_invoice_status()  # 🔄 Force order line update
            order._compute_invoice_status()  # 🔄 Force order update
        return invoices

    @api.onchange('project_id')
    def _onchange_project_id(self):
        """ Assign analytic account to all order lines based on selected project. """
        if self.project_id and self.project_id.analytic_account_id:
            analytic_account = self.project_id.analytic_account_id
            for line in self.order_line:
                line.analytic_distribution = {analytic_account.id: 100}

    @api.depends('name')
    def _compute_po_count(self):
        """ Count purchase orders linked to this sale order """
        for order in self:
            order.po_count = self.env['purchase.order'].sudo().search_count([('origin', '=', order.name)])

    def action_decline_estimation(self):
        """ Open the decline reason wizard (only approver can access) """
        # if self.approver_id != self.env.user and not self.env.user.has_group('base.group_system'):
        #     raise AccessError("Only the assigned approver or an Administrator can decline the estimation.")

        return {
            'name': 'Decline Estimation',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.decline.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sale_order_id': self.id},
        }

    def action_reset_to_approve(self):
        """
        Allows a Salesperson to edit a cancelled estimation
        and resend it for approval.
        """
        for order in self:
            if order.state == 'cancel':  # Ensure only canceled estimations are reset
                order.write({
                    'state': 'toapprove'
                })

    @api.depends('invoice_ids')
    def _compute_due_amount(self):
        """Compute the due amount based on unpaid invoices linked to the sale order."""
        for order in self:
            invoices = order.invoice_ids.filtered(lambda inv: inv.state not in ('cancel', 'draft'))
            order.due_amount = sum(invoices.mapped('amount_residual')) if invoices else 0.0

    @api.depends('invoice_ids.amount_residual')
    def _compute_has_due(self):
        """Check if the sale order has outstanding invoices."""
        for order in self:
            order.has_due = any(
                order.invoice_ids.filtered(lambda inv: inv.state != 'cancel' and inv.amount_residual > 0))

    @api.depends('amount_total')
    def _compute_is_warning(self):
        """Flag orders as warnings if their amount exceeds a defined threshold."""
        warning_threshold = 5000  # Example threshold value
        for order in self:
            order.is_warning = order.amount_total > warning_threshold

    @api.depends('user_id')
    def _compute_approver_id(self):
        """Assign the approver as the manager of the salesperson."""
        for order in self.filtered(lambda o: o.user_id):
            manager = order.user_id.sudo().employee_id.parent_id.user_id
            order.approver_id = manager.id if manager else None

    def write(self, vals):
        """Restrict changing approver_id to only the creator."""
        # if 'approver_id' in vals and any(order.user_id != self.env.user for order in self):
        #     raise UserError("Only the creator can change the Approver.")
        return super().write(vals)

    @api.model
    def create(self, vals):
        """Ensure only the creator can edit approver_id."""
        record = super().create(vals)
        # if 'approver_id' in vals and record.user_id != self.env.user:
        #     raise UserError("Only the creator can set the Approver.")
        return record

    def action_confirm(self):
        """ Ensure only ONE project is created per sale order and assigns the analytic account to all order lines. """
        res = super(BSSaleOrder, self).action_confirm()

        for order in self:

            # Check if a project already exists for this sale order
            existing_project = self.env['project.project'].search([('sale_order_id', '=', order.id)], limit=1)

            if existing_project:
                order.project_id = existing_project  # Ensure it's assigned
            else:
                # Get Customer Name and Reference Number
                customer_name = order.partner_id.name if order.partner_id else "Unknown Customer"
                reference_number = order.client_order_ref or order.name

                # Define Project Name Format
                project_name = f"{customer_name} | {reference_number}"

                # Create a new project if it does not exist
                new_project = self.env['project.project'].create({
                    'name': project_name,
                    'sale_order_id': order.id,
                    'partner_id': order.partner_id.id,  # Link project to the customer
                })
                order.project_id = new_project

            # Ensure an analytic account is created for the project only if it doesn't exist
            if not order.project_id.analytic_account_id:
                analytic_account_vals = {
                    'name': project_name,
                    'partner_id': order.partner_id.id,
                }

                # Get a default plan_id if required
                default_plan = self.env['account.analytic.plan'].search([], limit=1)

                # If `plan_id` is required and a plan exists, assign it
                if 'plan_id' in self.env['account.analytic.account']._fields and default_plan:
                    analytic_account_vals['plan_id'] = default_plan.id

                analytic_account = self.env['account.analytic.account'].create(analytic_account_vals)
                order.project_id.analytic_account_id = analytic_account

            # Assign the analytic account from the project to all order lines
            if order.project_id.analytic_account_id:
                for line in order.order_line:
                    line.analytic_distribution = {order.project_id.analytic_account_id.id: 100}

        return res

    def action_open_purchase_order(self):
        """Redirect to the new Purchase Order form, prefilled with customer data."""
        return {
            'name': 'Create Purchase Order',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
            'context': {
                'default_partner_id': self.partner_id.id,  # Prefill vendor field
                'default_origin': self.name,  # Link it to the Sale Order
            },
        }

    def action_reset_to_draft(self):
        """ Reset a cancelled estimation back to draft and resend for approval """
        for order in self:
            if order.state != 'cancel':
                raise UserError("You can only reset a cancelled estimation.")

            order.write({
                'state': 'estimate',
                'decline_reason': False,  # Clear the decline reason
            })

            order.message_post(body="Estimation has been reset to Draft and resent for approval.")

            return True

    def change_state(self, new_state):
        """Generic method to change the state if conditions are met."""
        state_machine = {
            'estimate': 'toapprove',
            'toapprove': 'draft',
            'sale': 'accounts',
        }
        for order in self.filtered(lambda o: o.state in state_machine and state_machine[o.state] == new_state):
            order.state = new_state

    def action_to_approve(self):
        self.state = 'toapprove'

    def action_approve(self):
        self.state = 'draft'

    def action_accounts(self):
        self.state = 'accounts'
