from odoo import _, api, fields, models, tools
from markupsafe import Markup
from odoo.exceptions import UserError


# ----------------------------------------------
class FileLine(models.Model):
    _name = "dms.line"
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']

    file_id = fields.Many2one('dms.file', store=True)
    dms_line_line = fields.One2many('dms.line.line', 'dms_line')
    dms_upload_file = fields.One2many('upload.file', 'dms_line')
    ref_dms_file = fields.Char(related='file_id.reference')
    change_log_ids = fields.One2many(
        'dms.file.change.log',
        'dms_line_id',
        string='Change Logs'
    )

    requester_id = fields.Many2one('res.users', default=lambda self: self.env.user.id)
    request_date = fields.Datetime()
    create_date = fields.Datetime(default=fields.Date.context_today)
    track_id = fields.Many2one('itrack.document.eat', 'iTrack')
    assign_to_id = fields.Many2one('hr.department', 'Assign To', domain="[('id', 'in', parent_root_department_ids)]")
    # department_to_id = fields.Many2one('hr.department', 'Department', domain="[('parent_id', '=', assign_to_id)]")
    employee_id = fields.Many2one('hr.employee', domain="[('id', 'in', employee_department)]")
    user_id = fields.Many2one('res.users', compute='_compute_name_of_employee')
    parent_root_dms = fields.Many2one('hr.department', domain="[('parent_id', '=', False)]",
                                      compute='_compute_parent_root')
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

    request_message = fields.Html(sanitize_attributes=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('wait', 'Wait'),
        ('in_progress', 'In Progress'),
        ('pending', 'Pending'),
        ('done', 'Done'),
    ], default='draft')
    can_reply = fields.Boolean()
    response_date = fields.Datetime()
    response_message = fields.Char()
    is_check = fields.Boolean()
    sequence = fields.Integer(string='Sequence', default=10)
    display_type = fields.Selection([
        ('line_section', "Section")],
        default=False, string="Type",
        help="Technical field for indicating the type of a line")
    is_section = fields.Boolean()
    # this is private chat
    channel_id = fields.Many2one('discuss.channel', 'Channel')
    request_access = fields.Boolean(compute='_compute_request_access')

    @api.depends('requester_id', 'user_id')
    def _compute_request_access(self):
        for req in self:
            if self.env.user._is_system() or self.env.user._is_admin() or self.env.user._is_superuser():
                req.request_access = True
            elif self.env.user.has_group('pds_itrack_eat.group_itrack_admin'):
                req.request_access = True
            elif self.env.uid in [req.requester_id.id, req.user_id.id]:
                req.request_access = True
            else:
                req.request_access = False

    #
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

    dm_file_count = fields.Integer(
        string='Document', compute='_compute_count_dms_file'
    )

    def _compute_count_dms_file(self):
        for record in self:
            print('_compute_count_itrack')
            record.dm_file_count = self.env['dms.file'].search_count([
                ('id', '=', record.file_id.id)
            ])

    def action_view_dms_file(self):
        print('action_view_itrack')
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'ITrack',
            'res_model': 'dms.file',
            'view_mode': 'tree,form',
            'domain': [('id', '=', self.file_id.id)],
            'context': dict(self.env.context, create=False),
        }

    change_log_count = fields.Integer(
        string='Change Log', compute='_compute_change_log'
    )

    def _compute_change_log(self):
        for record in self:
            record.change_log_count = self.env['dms.line.change.log'].search_count([
                ('dms_line_id', '=', record.id)
            ])

    def action_view_change_log(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Change log',
            'res_model': 'dms.line.change.log',
            'view_mode': 'tree,form',
            'domain': [('dms_line_id', '=', self.id)],
            'context': dict(self.env.context, create=False),
        }

    def action_reply(self):
        print('action_reply')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reply',
            'res_model': 'action.reply',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id},

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

    def action_assign_to(self):
        print('action_assign_to')
        dms_line = self.env['dms.line'].search([('id', '=', self.id)])
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assign To',
            'res_model': 'assign.to',
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
            rec.employee_id = self.env.user.employee_id.id
            rec.state = 'in_progress'

    @api.model
    def create(self, vals):
        vals['state'] = 'wait'
        return super(FileLine, self).create(vals)

    def write(self, vals):
        for record in self:
            for field, new_value in vals.items():
                old_value = record[field]
                field_info = self._fields[field]
                ttype = field_info.type

                if ttype == 'many2many' or ttype == 'one2many':
                    continue

                elif ttype == 'many2one' and old_value != new_value:
                    model_id = self.env['ir.model'].sudo().search([('model', '=', 'dms.line')]).id
                    field_object = self.env['ir.model.fields'].sudo().search(
                        [('name', '=', field), ('model_id', '=', model_id)])
                    record_name = self.env[f'{field_object.relation}'].sudo().search([('id', '=', new_value)]).name
                    self.env['dms.line.change.log'].sudo().create({
                        'dms_line_id': record.id,
                        'field_name': field_object.field_description,
                        'old_value': getattr(old_value, 'name', old_value) if old_value else None,
                        'new_value': record_name,
                        'user_id': self.env.uid,
                    })

                elif ttype == 'selection':
                    model_id = self.env['ir.model'].sudo().search([('model', '=', 'dms.line')]).id
                    field_object = self.env['ir.model.fields'].sudo().search(
                        [('name', '=', field), ('model_id', '=', model_id)])
                    selection_recs = field_object.selection_ids.sudo().search_read([('field_id', '=', field_object.id)])
                    for sel in selection_recs:
                        if sel['value'] == old_value:
                            old_value = sel['display_name']
                        if sel['value'] == new_value:
                            new_value = sel['display_name']

                    self.env['dms.line.change.log'].sudo().create({
                        'dms_line_id': record.id,
                        'field_name': field_object.field_description,
                        'old_value': old_value,
                        'new_value': new_value,
                        'user_id': self.env.uid,
                    })
                else:
                    model_id = self.env['ir.model'].sudo().search([('model', '=', 'dms.line')]).id
                    field_object = self.env['ir.model.fields'].sudo().search(
                        [('name', '=', field), ('model_id', '=', model_id)])
                    self.env['dms.line.change.log'].sudo().create({
                        'dms_line_id': record.id,
                        'field_name': field_object.field_description,
                        'old_value': old_value,
                        'new_value': new_value,
                        'user_id': self.env.uid,
                    })
        return super(FileLine, self).write(vals)


class DmsLineLine(models.Model):
    _name = 'dms.line.line'
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']

    dms_line = fields.Many2one('dms.line')
    requester_id = fields.Many2one('res.users', default=lambda self: self.env.user.id, store=True)

    assign_to_id = fields.Many2one('hr.department', 'Assign To', domain="[('id', 'in', parent_root_department_ids)]")
    parent_root_department_ids = fields.Many2many('hr.department', compute='_compute_parent_root_department_ids',
                                                  store=False, )
    employee_id = fields.Many2one('hr.employee', domain="[('id', 'in', employee_department)]")
    employee_department = fields.Many2many('hr.employee', compute='_compute_employee_department', store=False, )
    user_id = fields.Many2one('res.users', compute='_compute_name_of_employee', store=True)
    request_message = fields.Html(sanitize_attributes=False)
    response_date = fields.Datetime()
    response_message = fields.Html(sanitize_attributes=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('wait', 'Wait'),
        ('in_progress', 'In Progress'),
        ('pending', 'Pending'),
        ('done', 'Done'),
    ], default='draft')

    @api.onchange('employee_id')
    def _compute_name_of_employee(self):
        print('change name')
        for rec in self:
            rec.user_id = rec.employee_id.user_id.id

    @api.depends('dms_line.parent_root_dms')
    def _compute_parent_root_department_ids(self):
        for record in self:
            if record.dms_line.parent_root_dms:
                parent_root_id = record.dms_line.parent_root_dms.id
                record.parent_root_department_ids = self.env['hr.department'].search(
                    [('parent_root', '=', parent_root_id),
                     ('level', 'in', ['6', '7'])]
                )
            else:
                record.parent_root_department_ids = False

    @api.depends('dms_line.parent_root_dms')
    def _compute_employee_department(self):
        for record in self:
            if record.dms_line.parent_root_dms:
                parent_root_id = record.dms_line.parent_root_dms.id
                department = record.assign_to_id.id
                record.employee_department = self.env['hr.employee'].search(
                    [('ministry_id', '=', parent_root_id),
                     ('department_id', '=', department),
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

    # @api.model
    # def create(self, vals):
    #     print('Creating record with vals:', vals)
    #     employee = vals.get('employee_id')
    #     user = vals.get('user_id')
    #     requester = vals.get('requester_id')
    #     dms_line = vals.get('dms_line')
    #
    #     employee_id = employee if employee else None
    #     user_name = self.env['res.users'].browse(user).name if user else "Unknown User"
    #     requester_name = self.env['res.users'].browse(requester).name if requester else "Unknown Requester"
    #
    #     print('employee_id=', employee_id)
    #     print('user=', user)
    #     print('dms_line=', dms_line)
    #
    #     res = super(DmsLineLine, self).create(vals)
    #     model = 'dms.line'
    #     message = f'Mr. {requester_name} Assign To Mr. {user_name}'
    #
    #     print('user_name=', user_name)
    #     print('requester_name=', requester_name)
    #     print('message=', message)
    #
    #     # self.notify(user=user, message=message, model=model, id=dms_line)
    #
    #     return res

    # def notify(self, user=None, message="", model='dms.line', id=None):
    #     activity_type = self.env.ref('mail.mail_activity_data_todo')
    #     model_id = self.env['ir.model']._get(model).id
    #     print(user, '////', model_id, '//////')
    #     activity_id = self.env['mail.activity'].sudo().create({
    #         "activity_type_id": activity_type.id,
    #         "summary": message,
    #         "user_id": user,
    #         # "date_deadline": self.dms_line.create_date,
    #         "res_model_id": model_id,
    #         "res_id": id
    #     })


class UploadFile(models.Model):
    _name = 'upload.file'

    dms_line = fields.Many2one('dms.line')
    file_id = fields.Many2one('dms.file')
    ref_dms_file = fields.Char(related='file_id.reference')
    attachment_id = fields.Many2many(related='file_id.attachment_ids')

