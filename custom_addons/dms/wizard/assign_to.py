from odoo import _, api, fields, models, tools
from markupsafe import Markup
from datetime import datetime
from odoo.exceptions import UserError

class TransferTo(models.Model):
    _name = "assign.to"
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']

    # ----------------------------------------------
    dms_line = fields.Many2one('dms.line', string='ITrack')
    itrack_assignment_id = fields.Many2one('itrack.assignment')
    parent_root_dms = fields.Many2one('hr.department', domain="[('parent_id', '=', False)]",
                                      compute='_compute_parent_root')
    requester_id = fields.Many2one('res.users', default=lambda self: self.env.user.id)
    assign_to_id = fields.Many2one('hr.department', 'Assign To', domain="[('id', 'in', parent_root_department_ids)]")
    parent_root_department_ids = fields.Many2many('hr.department', compute='_compute_parent_root_department_ids',
                                                  store=False,)
    employee_id = fields.Many2one('hr.employee', domain="[('id', 'in', employee_department)]")
    employee_department = fields.Many2many('hr.employee', compute='_compute_employee_department', store=False, )
    user_id = fields.Many2one('res.users', compute='_compute_name_of_employee')
    request_message = fields.Html(sanitize_attributes=False)

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

    @api.onchange('employee_id')
    def _compute_name_of_employee(self):
        print('change name')
        for rec in self:
            rec.user_id = rec.employee_id.user_id.id

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

    @api.depends('parent_root_dms')
    def _compute_employee_department(self):
        for record in self:
            if record.parent_root_dms:
                parent_root_id = record.parent_root_dms.id
                record.employee_department = self.env['hr.employee'].search(
                    [('ministry_id', '=', parent_root_id),
                     ]
                )
            else:
                record.employee_department = False


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

    # ---------------------------------------------

    def action_assign(self):
        for rec in self:
            active_id = self.env.context.get('active_id')
            if not active_id:
                raise UserError("No active record found.")

            dms_line = self.env['dms.line'].browse(active_id)
            dms_line.ensure_one()

            create_dms_line_line = self.env['dms.line.line'].create({
                'dms_line': dms_line.id,
                'assign_to_id': rec.assign_to_id.id,
                'employee_id': rec.employee_id.id if rec.employee_id else False,
                'user_id': rec.user_id.id if rec.user_id else False,
                'request_message': rec.request_message,
                'state': 'wait',
            })
            itrack_requests = self.env['itrack.assignment'].create({
                'dms_line_id': dms_line.id,
                'dms_line_line_id': create_dms_line_line.id,
                'requester_id': self.requester_id.id,
                'assign_to_id': self.assign_to_id.id,
                'employee_id': rec.employee_id.id if rec.employee_id else False,
                'user_id': rec.user_id.id if rec.user_id else False,
                'request_date': fields.Datetime.now(),
                'request_message': self.request_message,
                'state': 'wait',
            })
            print('itrack_requests=', itrack_requests)

            user = self.user_id.id if self.user_id else False
            model = 'itrack.assignment'
            message = f'Mr. {self.requester_id.name} Assign To Mr. {self.user_id.name if self.user_id else "Unknown User"}'
            print('user=', user)
            print('message=', message)

            if user:
                self.notify(user=user, message=message, model=model, id=itrack_requests.id)
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