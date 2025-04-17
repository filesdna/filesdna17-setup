from odoo import models, fields, api
from odoo.exceptions import UserError


class ActionResend(models.TransientModel):
    _name = 'action.resend'

    requester_id = fields.Many2one(related='dms_line_id.requester_id', store=True)
    assign_to_id = fields.Many2one(related='dms_line_id.assign_to_id', store=True, string='Assign To')
    request_date = fields.Datetime(related='dms_line_id.request_date', store=True, string='Previously Date')
    request_date_new = fields.Datetime(default=fields.Date.context_today, string='New Date')
    response_message = fields.Char(related='dms_line_id.response_message', store=True, string='Previously Message')
    request_message_new = fields.Char(string='New Message')
    dms_line_id = fields.Many2one('dms.line')
    state = fields.Selection([
        ('pending', 'Pending'),
    ])

    def action_submit(self):
        print('action_submit')
        active_id = self.env.context.get('active_id')
        if not active_id:
            raise UserError("No active record found.")

        dms_line = self.env['dms.line'].browse(active_id)

        create_dms_resend = self.env['dms.line'].create({
            'requester_id': self.requester_id.id,
            'assign_to_id': self.assign_to_id.id,
            'request_date': self.request_date_new,
            'request_message': self.request_message_new,
            'file_id': dms_line.file_id.id,

        })
        dms_line.can_reply = True,
        dms_line.state = 'in_progress'
        print('create=', create_dms_resend)