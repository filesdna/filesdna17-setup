from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessError


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'To Approve'),
        ('verify', 'Verify'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('cancel', 'Rejected'),
    ], string="Status", readonly=True, copy=False, tracking=True, default='draft')

    def compute_sheet(self):
        """ Compute the payslip and move it to 'Verify' state """
        res = super(HrPayslip, self).compute_sheet()
        for slip in self:
            slip.write({'state': 'verify'})  # ✅ Moves to "Verify"
        return res

    def action_verify_payslip(self):
        """ Verify the payslip before approval """
        if not self.env.user.has_group('payroll.group_payroll_manager'):
            raise AccessError("Only Payroll Managers can verify payslips.")

        for slip in self:
            if slip.state not in ['to_approve', 'verify']:  # ✅ Allow verification from 'verify'
                raise ValidationError("Only payslips in 'To Approve' or 'Verify' state can be verified.")
            slip.state = 'verify'

    def action_approve_payslip(self):
        """ Approves the payslip """
        if not self.env.user.has_group('payroll.group_payroll_manager'):
            raise AccessError("Only Payroll Managers can approve payslips.")

        for slip in self:
            if slip.state != 'verify':  # ✅ Ensure approval comes after verification
                raise ValidationError("Payslip must be verified before approval.")
            slip.state = 'approved'

    def action_payslip_done(self):
        """ Mark the payslip as done """
        if not self.env.user.has_group('payroll.group_payroll_manager'):
            raise AccessError("Only Payroll Managers can finalize payslips.")

        for slip in self:
            if slip.state != 'approved':  # ✅ Prevent skipping the approval step
                raise ValidationError("Payslip must be approved before marking it as done.")
            slip.state = 'done'

    def action_cancel_payslip(self):
        """ Cancels the payslip """
        if not self.env.user.has_group('payroll.group_payroll_manager'):
            raise AccessError("Only Payroll Managers can cancel payslips.")

        for slip in self:
            if slip.state in ('done', 'cancel'):
                raise ValidationError("You cannot cancel a completed or already rejected payslip.")
            slip.state = 'cancel'

    def action_reject_payslip(self):
        """ Rejects the payslip """
        if not self.env.user.has_group('payroll.group_payroll_manager'):
            raise AccessError("Only Payroll Managers can reject payslips.")

        for slip in self:
            if slip.state not in ['to_approve', 'verify', 'approved']:
                raise ValidationError("Only pending or verified payslips can be rejected.")
            slip.state = 'cancel'

    def refund_sheet(self):
        """ Refund the payslip only if it is in 'done' state """
        if not self.env.user.has_group('payroll.group_payroll_manager'):
            raise AccessError("Only Payroll Managers can refund payslips.")

        for slip in self:
            if slip.state != 'done':
                raise ValidationError("You can only refund a completed payslip.")

            # Move payslip back to 'Draft' or create a reversed payslip
            slip.state = 'draft'
