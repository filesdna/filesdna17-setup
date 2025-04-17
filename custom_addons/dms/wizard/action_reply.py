from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime


class ActionReply(models.TransientModel):
    _name = 'action.reply'
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']

    response_date = fields.Datetime(default=fields.Date.context_today)
    response_message = fields.Selection([
        ('change_to_another_section', 'Change To Another Section'),
        ('save', 'Save'),
        ('continue', 'Continue'),
        ('export', 'Export'),
    ], default='save')

    # dms_line_id = fields.Many2one('dms.line')
    state = fields.Selection([
        ('done', 'Done'),
        ('in_progress', 'In Progress'),
        ('change_to_another_section', 'Change To Another Section'),
    ])
    dms_line_id = fields.Many2one('dms.line', string='ITrack', ondelete='cascade')
    dms_line_line_id = fields.Many2one('dms.line.line', string='ITrack', ondelete='cascade')
    itrack_assignment_id = fields.Many2one("itrack.assignment", string='My Assignment')
    requester_id = fields.Many2one('res.users', default=lambda self: self.env.user.id)
    transfer_to = fields.Many2one('res.users', store=True)
    transfer_date = fields.Datetime('Transfer Date', default=lambda self: datetime.now(), tracking=1)
    # ----------------------------------------------------------------------------------------------
    assign_to_id = fields.Many2one('hr.department', 'Assign To', domain="[('id', 'in', parent_root_department_ids)]")
    employee_id = fields.Many2one('hr.employee', domain="[('id', 'in', employee_department)]")
    user_id = fields.Many2one('res.users', compute='_compute_name_of_employee')
    parent_root_dms = fields.Many2one('hr.department', domain="[('parent_id', '=', False)]",
                                      compute='_compute_parent_root')
    request_message_change = fields.Html(sanitize_attributes=False)
    parent_root_department_ids = fields.Many2many(
        'hr.department',
        compute='_compute_parent_root_department_ids',
        store=False,
    )
    employee_department = fields.Many2many(
        'hr.employee',
        compute='_compute_employee_department',
        store=False,
    )

    @api.onchange('requester_id')
    def _compute_parent_root(self):
        user = self.env.user
        ministry_id = user.employee_id.ministry_id if user.employee_id else False
        for rec in self:
            if ministry_id:
                rec.parent_root_dms = ministry_id.id
            else:
                rec.parent_root_dms = False
            print('root=', ministry_id.name if ministry_id else 'No ministry assigned')

    @api.onchange('assign_to_id')
    def _onchange_assign_to_id(self):
        if self.assign_to_id:
            manager = self.assign_to_id.manager_id
            deputy = self.assign_to_id.deputy
            if manager:
                self.employee_id = manager.id
            else:
                self.employee_id = False
        else:
            self.employee_id = False

    @api.onchange('employee_id')
    def _compute_name_of_employee(self):
        for rec in self:
            rec.user_id = rec.employee_id.user_id.id

    @api.depends('parent_root_dms')
    def _compute_employee_department(self):
        for record in self:
            if record.parent_root_dms:
                parent_root_id = record.parent_root_dms.id
                record.employee_department = self.env['hr.employee'].search(
                    [('ministry_id', '=', parent_root_id)
                     ]
                )
            else:
                record.employee_department = False

    @api.depends('parent_root_dms')
    def _compute_parent_root_department_ids(self):
        for record in self:
            if record.parent_root_dms:
                parent_root_id = record.parent_root_dms.id
                record.parent_root_department_ids = self.env['hr.department'].search(
                    [('parent_root', '=', parent_root_id),
                     ('level', 'in', ['6', '7'])]
                )
            else:
                record.parent_root_department_ids = False

    # ----------------------------------------------------------------------------------------------

    @api.onchange('response_message')
    def _onchange_response_message(self):
        if self.response_message in ['save', 'export']:
            self.state = 'done'
        elif self.response_message == 'continue':
            self.state = 'in_progress'
        elif self.response_message == 'change_to_another_section':
            self.state = 'change_to_another_section'

    def action_submit(self):
        print('action_submit')
        active_id = self.env.context.get('active_id')
        print('active_id=', active_id)
        if not active_id:
            raise UserError("No active record found.")

        itrack_assignment = self.env['itrack.assignment'].browse(active_id)
        print('itrack_assignment=', itrack_assignment)
        #
        if self.response_message == 'continue':
            print('continue')
            self.dms_line_line_id.write({
                'response_date': self.response_date,
                'response_message': self.response_message,
                'state': 'in_progress',
            })
            itrack_assignment.write({
                'response_date': self.response_date,
                'response_message': self.response_message,
            })

        elif self.response_message in ['save', 'export']:
            self.state = 'done'
            self.dms_line_line_id.write({
                'response_date': self.response_date,
                'response_message': self.response_message,
                'state': 'done',
            })
            itrack_assignment.write({
                'response_date': self.response_date,
                'response_message': self.response_message,
            })

        elif self.state == 'change_to_another_section':
            self.dms_line_line_id.write({
                'response_message': self.response_message,
                'response_date': self.response_date,
                'state': 'in_progress',
            })
            assign_to_id = self.dms_line_line_id.assign_to_id.id
            create_dms_line_line_change = self.dms_line_line_id.create({
                'dms_line': self.dms_line_line_id.dms_line.id,
                'requester_id': self.requester_id.id,
                'assign_to_id': self.assign_to_id.id,
                'employee_id': self.employee_id.id,
                'user_id': self.employee_id.user_id.id,
                'request_message': self.request_message_change,
                'state': 'in_progress',
            })
            print('create_dms_line_line_change=', create_dms_line_line_change)
            create_dms_line = self.env['dms.line'].create({
                'file_id': self.dms_line_line_id.dms_line.file_id.id,
                'create_date': self.transfer_date,

            })
            print('create_dms_line=', create_dms_line)
            create_dms_line_line = self.env['dms.line.line'].create({
                'dms_line': create_dms_line.id,
                # 'dms_line_line_id': create_dms_line_line_change.id,
                # 'parent_id': dms_line.id,
                'requester_id': self.requester_id.id,
                'assign_to_id': self.assign_to_id.id,
                'employee_id': self.employee_id.id,
                'user_id': self.employee_id.user_id.id,
                'request_message': self.request_message_change,
                'state': 'wait',
            })
            print('create_dms_line_line=', create_dms_line_line)
            self.itrack_assignment_id.create({
                'dms_line_id': create_dms_line.id,
                'dms_line_line_id': create_dms_line_line.id,
                'parent_id': itrack_assignment.id,
                'requester_id': self.requester_id.id,
                'request_date': self.transfer_date,
                'assign_to_id': self.assign_to_id.id,
                'employee_id': self.employee_id.id,
                'user_id': self.employee_id.user_id.id,
                'request_message': self.request_message_change,
                'state': create_dms_line_line.state == 'in_progress',
            })
            itrack_assignment.write({
                'response_date': self.response_date,  # self.dms_line_line_id.response_date
                'response_message': self.response_message,
            })
            user = self.user_id.id if self.user_id else False
            model = 'dms.line'
            message = f'Mr. {self.requester_id.name} Assign To Mr. {self.user_id.name if self.user_id else "Unknown User"}'
            print('user=', user)
            print('message=', message)

            if user:
                self.notify(user=user, message=message, model=model, id=create_dms_line.id)

    def notify(self, user=None, message="", model='itrack.assignment', id=None):
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        model_id = self.env['ir.model']._get(model).id
        print(user, '////', model_id, '//////')
        activity_id = self.env['mail.activity'].sudo().create({
            "activity_type_id": activity_type.id,
            "summary": message,
            "user_id": user,
            "date_deadline": self.create_date,
            "res_model_id": model_id,
            "res_id": id
        })