from odoo import models, fields, api
from odoo.exceptions import AccessError, UserError

class SaleOrderDeclineWizard(models.TransientModel):
    _name = 'sale.order.decline.wizard'
    _description = 'Decline Estimation Wizard'

    sale_order_id = fields.Many2one('sale.order', string="Sale Order", required=True)
    reason = fields.Text(string="Decline Reason", required=True)

    def confirm_decline(self):
        print('confirm_decline')
        self.ensure_one()

        # Allow the assigned approver or an administrator
        if (self.sale_order_id.approver_id or False) != self.env.user and not self.env.user.has_group('base.group_system'):
            raise AccessError("Only the assigned approver or an Administrator can decline the estimation.")

        if not self.reason:
            raise UserError("Please provide a reason for declining the estimation.")

        self.sale_order_id.write({
            'state': 'estimate',
            'decline_reason': self.reason
        })
        self.sale_order_id.message_post(body=f"Estimation declined. Reason: {self.reason}")

        return {'type': 'ir.actions.act_window_close'}
