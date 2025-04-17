from odoo import models, fields, api, _


class HrDepartment(models.Model):
    _inherit = 'hr.department'
    _description = "Department"
    _order = "name"
    _rec_name = 'complete_name'
    _parent_store = True

    number = fields.Char()
    deputy = fields.Many2one('hr.employee')
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', recursive=True, store=True)
    level = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
    ])
    parent_root = fields.Many2one('hr.department', domain="[('parent_id', '=', False)]")
    # -----------------------------------------------------------------------------------
    name = fields.Char(required=True, translate=True)
    root_parent = fields.Many2one('hr.department', domain="[('level', '=', 2)]")
    main_parent = fields.Many2one('hr.department')
    parent_id = fields.Many2one('hr.department', index=True, check_company=True)
    parent_id_new = fields.Many2one('hr.department', domain="[('level', '=', 2)]")
    top_formation = fields.Boolean()

    @api.onchange('top_formation')
    def _onchange_top_formation(self):
        for rec in self:
            if rec.top_formation:
                print('hhh')

    def _set_parent_root(self, department):
        if department.parent_id:
            department.parent_root = department.parent_id.parent_root or department.parent_id
        else:
            department.parent_root = department.complete_name

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for department in self:
            if department.parent_id:
                department.complete_name = department.name
            else:
                department.complete_name = department.name

    @api.model
    def create(self, vals):
        res = super(HrDepartment, self).create(vals)
        if res.parent_id:
            res.parent_root = res.parent_id.parent_root or res.parent_id

        # if res.parent_id and res.parent_id.is_section:
        #     res.is_department = True

        return res

    def write(self, vals):
        if 'parent_id' in vals:
            for record in self:
                if vals['parent_id']:
                    parent_department = self.browse(vals['parent_id'])
                    record.parent_root = parent_department.parent_root or parent_department
                else:
                    record.parent_root = False
        return super(HrDepartment, self).write(vals)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    ministry_id = fields.Many2one('hr.department', domain="[('parent_id', '=', False)]")
    level_1 = fields.Many2one('hr.department', domain="[('id', 'in', parent_root_ministry_id)]")
    parent_root_ministry_id = fields.Many2many(
        'hr.department',
        compute='_compute_parent_root_ministry_id',
        store=False,
    )

    @api.depends('ministry_id')
    def _compute_parent_root_ministry_id(self):
        for record in self:
            if record.ministry_id and record.ministry_id.child_ids:
                child_ids = record.ministry_id.child_ids.ids
                record.parent_root_ministry_id = self.env['hr.department'].search(
                    [('id', 'in', child_ids)]
                )
            else:
                record.parent_root_ministry_id = False

    level_2 = fields.Many2one('hr.department', domain="[('id', 'in', parent_root_level_1)]")
    parent_root_level_1 = fields.Many2many(
        'hr.department',
        compute='_compute_parent_root_level_1',
        store=False,
    )

    @api.depends('level_1')
    def _compute_parent_root_level_1(self):
        for record in self:
            if record.level_1 and record.level_1.child_ids:
                child_ids = record.level_1.child_ids.ids
                record.parent_root_level_1 = self.env['hr.department'].search(
                    [('id', 'in', child_ids)]
                )
            else:
                record.parent_root_level_1 = False

    level_3 = fields.Many2one('hr.department', domain="[('id', 'in', parent_root_level_2)]")
    parent_root_level_2 = fields.Many2many(
        'hr.department',
        compute='_compute_parent_root_level_2',
        store=False,
    )

    @api.depends('level_2')
    def _compute_parent_root_level_2(self):
        for record in self:
            if record.level_2 and record.level_2.child_ids:
                child_ids = record.level_2.child_ids.ids
                record.parent_root_level_2 = self.env['hr.department'].search(
                    [('id', 'in', child_ids)]
                )
            else:
                record.parent_root_level_2 = False

    level_4 = fields.Many2one('hr.department', domain="[('id', 'in', parent_root_level_3)]")
    parent_root_level_3 = fields.Many2many(
        'hr.department',
        compute='_compute_parent_root_level_3',
        store=False,
    )

    @api.depends('level_3')
    def _compute_parent_root_level_3(self):
        for record in self:
            if record.level_3 and record.level_3.child_ids:
                child_ids = record.level_3.child_ids.ids
                record.parent_root_level_3 = self.env['hr.department'].search(
                    [('id', 'in', child_ids)]
                )
            else:
                record.parent_root_level_3 = False

    level_5 = fields.Many2one('hr.department', domain="[('id', 'in', parent_root_level_4)]")
    parent_root_level_4 = fields.Many2many(
        'hr.department',
        compute='_compute_parent_root_level_4',
        store=False,
    )

    @api.depends('level_4')
    def _compute_parent_root_level_4(self):
        for record in self:
            if record.level_4 and record.level_4.child_ids:
                child_ids = record.level_4.child_ids.ids
                record.parent_root_level_4 = self.env['hr.department'].search(
                    [('id', 'in', child_ids)]
                )
            else:
                record.parent_root_level_4 = False

    level_6 = fields.Many2one('hr.department', domain="[('id', 'in', parent_root_level_5)]")
    parent_root_level_5 = fields.Many2many(
        'hr.department',
        compute='_compute_parent_root_level_5',
        store=False,
    )

    @api.depends('level_5')
    def _compute_parent_root_level_5(self):
        for record in self:
            if record.level_5 and record.level_5.child_ids:
                child_ids = record.level_5.child_ids.ids
                record.parent_root_level_5 = self.env['hr.department'].search(
                    [('id', 'in', child_ids)]
                )
            else:
                record.parent_root_level_5 = False

    level_7 = fields.Many2one('hr.department', domain="[('id', 'in', parent_root_level_6)]")
    parent_root_level_6 = fields.Many2many(
        'hr.department',
        compute='_compute_parent_root_level_6',
        store=False,
    )

    @api.depends('level_6')
    def _compute_parent_root_level_6(self):
        for record in self:
            if record.level_6 and record.level_6.child_ids:
                child_ids = record.level_6.child_ids.ids
                record.parent_root_level_6 = self.env['hr.department'].search(
                    [('id', 'in', child_ids)]
                )
            else:
                record.parent_root_level_6 = False

    level_8 = fields.Many2one('hr.department', domain="[('id', 'in', parent_root_level_7)]")
    parent_root_level_7 = fields.Many2many(
        'hr.department',
        compute='_compute_parent_root_level_7',
        store=False,
    )

    @api.depends('level_7')
    def _compute_parent_root_level_7(self):
        for record in self:
            if record.level_7 and record.level_7.child_ids:
                child_ids = record.level_7.child_ids.ids
                record.parent_root_level_7 = self.env['hr.department'].search(
                    [('id', 'in', child_ids)]
                )
            else:
                record.parent_root_level_7 = False

    level_9 = fields.Many2one('hr.department', domain="[('id', 'in', parent_root_level_8)]")
    parent_root_level_8 = fields.Many2many(
        'hr.department',
        compute='_compute_parent_root_level_8',
        store=False,
    )

    @api.depends('level_8')
    def _compute_parent_root_level_8(self):
        for record in self:
            if record.level_8 and record.level_8.child_ids:
                child_ids = record.level_8.child_ids.ids
                record.parent_root_level_8 = self.env['hr.department'].search(
                    [('id', 'in', child_ids)]
                )
            else:
                record.parent_root_level_8 = False

    level_10 = fields.Many2one('hr.department', domain="[('id', 'in', parent_root_level_9)]")
    parent_root_level_9 = fields.Many2many(
        'hr.department',
        compute='_compute_parent_root_level_9',
        store=False,
    )

    @api.depends('level_9')
    def _compute_parent_root_level_9(self):
        for record in self:
            if record.level_9 and record.level_9.child_ids:
                child_ids = record.level_9.child_ids.ids
                record.parent_root_level_9 = self.env['hr.department'].search(
                    [('id', 'in', child_ids)]
                )
            else:
                record.parent_root_level_9 = False

    # directorate_id = fields.Many2one('hr.department', domain="[('parent_id', '=', office_id)]")
    # section_id = fields.Many2one('hr.department',
    #                              domain="[('parent_id', '=', directorate_id),('parent_root', '=', ministry_id), ('level', '=', 6)]")
    # department_id = fields.Many2one(compute='_compute_unit_number')
    root_unit_id = fields.Char(compute='_compute_unit_number')
    unit_id = fields.Char(compute='_compute_unit_number')

    @api.onchange('level_1', 'level_2', 'level_3', 'level_4', 'level_5', 'level_6', 'level_7', 'level_8', 'level_9',
                  'level_10')
    def _onchange_level(self):
        for record in self:
            for level in range(10, 0, -1):
                level_field = f'level_{level}'
                if getattr(record, level_field):
                    record.department_id = getattr(record, level_field).id
                    break

    @api.onchange('department_id')
    def _compute_unit_number(self):
        for record in self:
            record.unit_id = ''
            record.root_unit_id = ''
            record.department_id = ''

            for level in range(10, 0, -1):
                level_field = f'level_{level}'  # search from 10 to 0 and stop at last level you add it
                print('level_field=', level_field)
                if getattr(record, level_field):  # check if level_field is empty value or no
                    record.unit_id = getattr(record, level_field).number
                    record.root_unit_id = getattr(record, level_field).parent_id.number
                    record.department_id = getattr(record, level_field).id
                    break

    # Box File
    files_count = fields.Integer(
        string='Files', compute='_compute_count_files'
    )

    def _compute_count_files(self):
        for record in self:
            config_param = self.env["ir.config_parameter"].sudo()
            enable_document_tags_filtering = config_param.get_param("dms.enable_document_tags_filtering",
                                                                    default="True") == "True"
            filter_tags_str = config_param.get_param("dms.filter_tags", default="")
            if enable_document_tags_filtering and filter_tags_str:
                filter_tags_list = [tag.strip() for tag in filter_tags_str.split(',')] if filter_tags_str else []
                file_employee_count = self.env['dms.file'].search_count([
                    ('create_uid', '=', record.user_id.id),
                    ('tag_ids.name', 'in', filter_tags_list),
                ])
                record.files_count = file_employee_count
            else:
                file_employee_count = self.env['dms.file'].search_count([
                    ('create_uid', '=', record.user_id.id),
                ])
                record.files_count = file_employee_count

    def action_view_files(self):
        print('action_view_files')
        config_param = self.env["ir.config_parameter"].sudo()
        enable_document_tags_filtering = config_param.get_param("dms.enable_document_tags_filtering",
                                                                default="True") == "True"
        filter_tags_str = config_param.get_param("dms.filter_tags", default="")
        if enable_document_tags_filtering and filter_tags_str:
            filter_tags_list = [tag.strip() for tag in filter_tags_str.split(',')] if filter_tags_str else []
            self.ensure_one()
            return {
                'type': 'ir.actions.act_window',
                'name': 'Files',
                'res_model': 'dms.file',
                'view_mode': 'tree,form',
                'domain': [('create_uid', '=', self.user_id.id), ('tag_ids.name', 'in', filter_tags_list)],
                'context': dict(self.env.context, create=False),
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Files',
                'res_model': 'dms.file',
                'view_mode': 'tree',
                'domain': [('create_uid', '=', self.user_id.id)],
                'context': dict(self.env.context, create=False),
            }
