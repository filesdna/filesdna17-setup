from odoo import _, api, fields, models, tools
from markupsafe import Markup
from odoo.exceptions import UserError


# ----------------------------------------------
class FileLine(models.Model):
    _name = "itrack.assignment"
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']
    _description = 'Itrack Request'

    # channel_id = fields.Many2one('discuss.channel', 'Channel')
    name = fields.Many2one(related='assign_to_id', string='Name')
    dms_line_id = fields.Many2one('dms.line', 'iTrack')
    dms_line_line_id = fields.Many2one('dms.line.line')
    # track_name = fields.Char(related='track_id.name', store=True)
    requester_id = fields.Many2one('res.users', 'Requester', default=lambda self: self.env.user.id, )
    assign_to_id = fields.Many2one('hr.department', 'Assign To')
    request_date = fields.Datetime('Request Date')
    response_date = fields.Datetime('Response Date')
    request_message = fields.Html(sanitize_attributes=False)
    response_message = fields.Text('Response Message')
    state = fields.Selection(related='dms_line_line_id.state')
    employee_id = fields.Many2one('hr.employee')
    user_id = fields.Many2one('res.users', compute='_compute_name_of_employee', store=True)
    # request_access = fields.Boolean(compute='_compute_request_access')
    can_reply = fields.Boolean(compute='_compute_can_reply')
    channel_id = fields.Many2one('discuss.channel', 'Channel')
    request_access = fields.Boolean(compute='_compute_request_access')
    parent_id = fields.Many2one('itrack.assignment', string='Parent Request', index=True)


    @api.onchange('employee_id')
    def _compute_name_of_employee(self):
        for rec in self:
            rec.user_id = rec.employee_id.user_id.id

    #
    @api.depends('assign_to_id')
    def _compute_can_reply(self):
        for req in self:
            if self.env.uid == req.assign_to_id.id and not req.response_date:
                req.can_reply = True
            else:
                req.can_reply = False

    def action_reply(self):
        print('action_reply')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reply',
            'res_model': 'action.reply',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'default_dms_line_line_id': self.dms_line_line_id.id,  # Set the default value here
            },
        }

    def action_resend(self):
        dms_line = self.env['dms.line'].search([('id', '=', self.id)])
        print('Dms ID:', dms_line)
        print('action_resend')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Resend',
            'res_model': 'action.resend',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_dms_line_id': self.id,
            },
        }

    def action_accept(self):
        print('action_accept')
        for rec in self:
            if rec.dms_line_line_id:
                print('dms_line_line_id=', rec.dms_line_line_id)
                # Ensure that dms_line_line is accessible
                if rec.dms_line_line_id:
                    rec.dms_line_line_id.employee_id = self.env.user.employee_id.id
                    rec.dms_line_line_id.user_id = rec.employee_id.user_id.id
                    rec.dms_line_line_id.state = 'in_progress'
                else:
                    raise UserError("DMS Line Line is not found.")
            # if rec:
            #     rec.employee_id = self.env.user.employee_id.id
            #     rec.user_id = rec.employee_id.user_id.id
            #     rec.state = 'in_progress'

    @api.depends('requester_id', 'user_id')
    def _compute_request_access(self):
        for req in self:
            if self.env.user._is_system() or self.env.user._is_admin() or self.env.user._is_superuser():
                req.request_access = True
            elif self.env.user.has_group('pds_itrack_eat.group_itrack_admin'):
                req.request_access = True
            elif self.env.uid in [req.requester_id.id, req.assign_to_id.id]:
                req.request_access = True
            else:
                req.request_access = False

    def refresh_channel(self, channel_id, is_new):
        self.ensure_one()
        self.write({'channel_id': channel_id})
        partner_ids = [self.requester_id.partner_id.id, self.user_id.partner_id.id]
        discuss_channel = self.env['discuss.channel'].browse(channel_id)
        discuss_channel.write({'itrack_channel': True})
        discuss_channel.add_members(list(set(partner_ids)))
        if is_new:
            self.post_channel_message(discuss_channel, self.requester_id.partner_id, self.request_message)
            self.post_channel_message(discuss_channel, self.user_id.partner_id, self.response_message)

    def post_channel_message(self, channel_id, partner_id, message):
        if not channel_id or not partner_id or not message:
            return
        member = self.env['discuss.channel.member'].search([('channel_id', '=', channel_id.id),
                                                            ('partner_id', '=', partner_id.id)], limit=1)
        member.channel_id.message_post(
            body=Markup('<div class="o_mail_notification">%s</div>') % message,
            message_type="comment", subtype_xmlid="mail.mt_comment", author_id=partner_id.id)

    def action_open_itrack(self):
        return {
            'res_model': 'dms.line',
            'type': 'ir.actions.act_window',
            'views': [[False, "form"]],
            'res_id': self.dms_line_id.id,
            'context': {'from_request': True},
        }

    #
    # def notify_user(self, request=True):
    #     for req in self:
    #         if request:
    #             message = '%(user)s send the iTrack request, you can have a <a href="%(itrack_link)s">CLICK HERE</a> to review.'
    #             subject = 'iTrack New Request'
    #             requester = req.assign_to_id.partner_id
    #             responsible = req.requester_id.partner_id
    #             message2 = req.request_message
    #         else:
    #             message = '%(user)s give you the iTrack feedback, you can <a href="%(itrack_link)s">CLICK HERE</a> to review.'
    #             subject = 'iTrack Response'
    #             requester = req.requester_id.partner_id
    #             responsible = req.assign_to_id.partner_id
    #             message2 = req.response_message
    #         itrack_link = req.track_id._notify_get_action_link('view')
    #         self.env['mail.thread'].sudo().message_notify(
    #             partner_ids=[requester.id],
    #             model_description='iTrack',
    #             subject=_(subject),
    #             body=Markup(message % {'user': responsible.name, 'itrack_link': itrack_link}),
    #             email_layout_xmlid='mail.mail_notification_light',
    #         )
    #         self.post_channel_message(req.channel_id, responsible, message2)
