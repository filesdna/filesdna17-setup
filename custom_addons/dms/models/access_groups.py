from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DmsAccessGroups(models.Model):
    _name = "dms.access.group"
    _description = "Record Access Groups"
    _parent_store = True
    _parent_name = "parent_group_id"

    name = fields.Char(string="Group Name", required=True, translate=True)
    parent_path = fields.Char(index=True)

    # Permissions written directly on this group
    perm_write = fields.Boolean(string="Edit Access")
    perm_download = fields.Boolean(string="Download Access")
    perm_lock = fields.Boolean(string="Lock Access")
    perm_unlock = fields.Boolean(string="UnLock Access")
    perm_encrypt = fields.Boolean(string="Encrypt Access")
    perm_rename = fields.Boolean(string="Rename Access")
    perm_is_root = fields.Boolean(string="Is Root/Directory")
    perm_full_admin = fields.Boolean(string="Full Admin Access")
    is_full_admin = fields.Boolean(string="Full Admin Access", compute="compute_perm_full_admin", store=True,
                                   readonly=False)
    # ------------------------------------------------------------
    perm_open_locally = fields.Boolean(string="Perm Open Locally")
    perm_edit_online = fields.Boolean(string="Perm Edit Online")
    perm_preview_file = fields.Boolean(string="Perm Preview File")
    company_id = fields.Many2one(
        string='Company',
        comodel_name='res.company',
        required=True,
        readonly=True,
        default=lambda self: self.env.user.company_id)
    # document_ids = fields.One2many('dms.access.group.line', 'access_id')
    parameter_values_access = fields.One2many('dms.link.document.parameter.line', 'access_id',
                                              string="Document Parameters")
    enable_document_filter = fields.Boolean(
        string='Enable Document Filter',
        store=True,)

    @api.onchange('enable_document_filter')
    def _compute_enable_document_filter(self):
        config = self.env['ir.config_parameter'].sudo()
        self.enable_document_filter = config.get_param("dms.enable_document_filter", "False") == "True"

    # --------------------------Files&Directories----------------------------------
    perm_create = fields.Boolean(string="Create Files")
    perm_unlink = fields.Boolean(string="Delete Files")

    perm_create_directory = fields.Boolean(string='Create Directory')
    perm_delete_directory = fields.Boolean(string='Delete Directory')

    # -----------------------------------------------------------------------------
    @api.onchange('perm_full_admin')
    def compute_perm_full_admin(self):
        for rec in self:
            if rec.perm_full_admin == True:
                rec.perm_create = True
                rec.perm_write = True
                rec.perm_download = True
                rec.perm_lock = True
                rec.perm_unlock = True
                rec.perm_encrypt = True
                rec.perm_rename = True
                rec.perm_unlink = True
                rec.perm_open_locally = True
                rec.perm_edit_online = True
                rec.perm_preview_file = True
                rec.perm_create_directory = True
                rec.perm_delete_directory = True
                rec.perm_is_root = True
                rec.is_full_admin = True
            else:
                rec.perm_create = False
                rec.perm_write = False
                rec.perm_download = False
                rec.perm_lock = False
                rec.perm_unlock = False
                rec.perm_encrypt = False
                rec.perm_rename = False
                rec.perm_unlink = False
                rec.perm_open_locally = False
                rec.perm_edit_online = False
                rec.perm_preview_file = False
                rec.perm_create_directory = False
                rec.perm_delete_directory = False
                rec.perm_is_root = False
                rec.is_full_admin = False

    # --------------------Directories Settings------------------
    @api.onchange('perm_create_directory')
    def change_create_access(self):
        for rec in self:  # Iterate over each record
            # print('group of user=', rec.users.groups_id.mapped('name'))
            # print('accesses_count=', rec.users.accesses_count)
            create_directory_group = self.env.ref('dms.group_create_dms_directory', raise_if_not_found=False)
            print('create_directory_group=', create_directory_group.name)
            if rec.perm_create_directory:
                if create_directory_group not in rec.users.groups_id:
                    rec.users.groups_id = [(4, create_directory_group.id)]
                    print('group after add=', rec.users.groups_id.mapped('name'))
            else:
                if create_directory_group:
                    rec.users.groups_id = [(3, create_directory_group.id)]
                    print('group after remove=', rec.users.groups_id.mapped('name'))

    @api.onchange('perm_delete_directory')
    def change_delete_access(self):
        print('group of user=', self.users.groups_id.mapped('name'))
        for rec in self:
            delete_directory_group = self.env.ref('dms.group_delete_dms_directory', raise_if_not_found=False)
            print('delete_file_group=', delete_directory_group.name)
            if rec.perm_delete_directory:
                if delete_directory_group not in rec.users.groups_id:
                    rec.users.groups_id = [(4, delete_directory_group.id)]
                    print('group after add=', self.users.groups_id.mapped('name'))
            else:
                if delete_directory_group:
                    rec.users.groups_id = [(3, delete_directory_group.id)]
                    print('group after remove=', self.users.groups_id.mapped('name'))

    @api.onchange('explicit_user_ids')
    def change_explicit_user_access(self):
        for rec in self:
            create_directory_group = self.env.ref('dms.group_create_dms_directory', raise_if_not_found=False)
            delete_directory_group = self.env.ref('dms.group_delete_dms_directory', raise_if_not_found=False)
            print('create_file_group=', create_directory_group)
            print('delete_file_group=', delete_directory_group)
            if create_directory_group or delete_directory_group:
                for user in rec.explicit_user_ids:
                    print('user=', user)
                    if rec.perm_create_directory or rec.perm_delete_directory:
                        if create_directory_group or delete_directory_group not in user.groups_id:
                            user.groups_id = [(4, create_directory_group.id), (4, delete_directory_group.id)]
                    else:
                        if create_directory_group or delete_directory_group in user.groups_id:
                            user.groups_id = [(3, create_directory_group.id), (3, delete_directory_group.id)]

    # Permissions computed including parent group
    perm_inclusive_create = fields.Boolean(
        string="Inherited Create Access",
        compute="_compute_inclusive_permissions",
        store=True,
        recursive=True,
    )
    perm_inclusive_write = fields.Boolean(
        string="Inherited Write Access",
        compute="_compute_inclusive_permissions",
        store=True,
        recursive=True,
    )
    perm_inclusive_unlink = fields.Boolean(
        string="Inherited Unlink Access",
        compute="_compute_inclusive_permissions",
        store=True,
        recursive=True,
    )

    directory_ids = fields.Many2many(
        comodel_name="dms.directory",
        relation="dms_directory_groups_rel",
        string="Directories",
        column1="gid",
        column2="aid",
        auto_join=True,
        readonly=False,
    )
    complete_directory_ids = fields.Many2many(
        comodel_name="dms.directory",
        relation="dms_directory_complete_groups_rel",
        column1="gid",
        column2="aid",
        string="Complete directories",
        auto_join=True,
        readonly=True,
    )
    count_users = fields.Integer(compute="_compute_users", store=True)
    count_directories = fields.Integer(compute="_compute_count_directories")
    parent_group_id = fields.Many2one(
        comodel_name="dms.access.group",
        string="Parent Group",
        ondelete="cascade",
        index=True,
    )

    child_group_ids = fields.One2many(
        comodel_name="dms.access.group",
        inverse_name="parent_group_id",
        string="Child Groups",
    )
    group_ids = fields.Many2many(
        comodel_name="res.groups",
        relation="dms_access_group_groups_rel",
        column1="gid",
        column2="rid",
        string="Groups",
    )
    explicit_user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="dms_access_group_explicit_users_rel",
        column1="gid",
        column2="uid",
        string="Explicit Users",
        domain=lambda self: self._get_company_id_domain()

    )

    @api.onchange('explicit_user_ids')
    def add_access_for_users(self):
        self.ensure_one()
        for rec in self:
            if rec.explicit_user_ids:
                access_ids = []
                for user in rec.explicit_user_ids:
                    id = str(self.id)
                    access_id = int(id.split('_')[1])  # Assuming this is the ID you want to add
                    access_ids.append(access_id)  # Collecting access IDs

                    user_access_search = self.env['res.users'].search([('name', '=', user.name)])
                    if user_access_search:
                        print('user_access_search=', user_access_search.name)
                        # Update user's access_id_many field
                        user_access_search.write({
                            'access_id_many': [(4, access_id)]  # Adding the access ID to the Many2many field
                        })

    users = fields.Many2many(
        comodel_name="res.users",
        relation="dms_access_group_users_rel",
        column1="gid",
        column2="uid",
        string="Group Users",
        compute="_compute_users",
        auto_join=True,
        store=True,
        recursive=True,
    )

    @api.depends("directory_ids")
    def _compute_count_directories(self):
        for record in self:
            record.count_directories = len(record.directory_ids)

    _sql_constraints = [
        ("name_uniq", "unique (name)", "The name of the group must be unique!")
    ]

    @api.depends(
        "parent_group_id.perm_inclusive_create",
        "parent_group_id.perm_inclusive_unlink",
        "parent_group_id.perm_inclusive_write",
        "parent_path",
        "perm_create",
        "perm_unlink",
        "perm_write",
    )
    def _compute_inclusive_permissions(self):
        """Provide full permissions inheriting from parent recursively."""
        for one in self:
            one.update(
                {
                    "perm_inclusive_%s"
                    % perm: (
                            one["perm_%s" % perm]
                            or one.parent_group_id["perm_inclusive_%s" % perm]
                    )
                    for perm in ("create", "unlink", "write")
                }
            )

    @api.model
    def default_get(self, fields_list):
        res = super(DmsAccessGroups, self).default_get(fields_list)
        parameters = self.env['document.parameters'].search([])
        print('parameters-----------------=', parameters)
        res = super(DmsAccessGroups, self).default_get(fields_list)

        res['parameter_values_access'] = [
            (0, 0, {'parameter_id': param.id}) for param in parameters
        ]
        return res

    @api.depends(
        "parent_group_id",
        "parent_group_id.users",
        "group_ids",
        "group_ids.users",
        "explicit_user_ids",
    )
    def _compute_users(self):
        for record in self:
            users = record.mapped("group_ids.users")
            users |= record.mapped("explicit_user_ids")
            users |= record.mapped("parent_group_id.users")
            record.update({"users": users, "count_users": len(users)})

    @api.constrains("parent_path")
    def _check_parent_recursiveness(self):
        """Forbid recursive relationships."""
        for one in self:
            if not one.parent_group_id:
                continue
            if str(one.id) in one.parent_path.split("/"):
                raise ValidationError(
                    _("Parent group '%(parent)s' is child of '%(current)s'.")
                    % {
                        "parent": one.parent_group_id.display_name,
                        "current": one.display_name,
                    }
                )

    @api.model
    def _get_company_id_domain(self):
        company_id = self.env.company.id
        return [('company_id', '=', company_id)]

    # @api.model
    # def create(self, vals):
    #     res = super(DmsAccessGroups, self).create(vals)
    #     parameter_values_access = vals.get("parameter_values_access", [])
    #     print('res=', res)
    #     print('parameter_values=', parameter_values_access)
    #     document_parameters = self.env['document.parameters'].search([('required', '=', True)])
    #     print('document_parameters=', document_parameters.mapped('name'))
    #     for pv in parameter_values_access:
    #         if pv[0] == 0 and not pv[2].get("selected_value_ids"):
    #             raise ValidationError("Please select a value for all document parameters before saving.")
    #     return res

    # @api.model
    # def create(self, vals):
    #     # Call the super method to create the record
    #     res = super(DmsAccessGroups, self).create(vals)
    #
    #     # Get parameter_values_access from vals
    #     parameter_values_access = vals.get("parameter_values_access", [])
    #     print('res=', res)
    #     document_parameters = self.env['document.parameters'].search([('required', '=', True)])
    #     print('document_parameters=', document_parameters.mapped('name'))
    #
    #     # Ensure parameter_id is a valid field
    #     if hasattr(document_parameters, 'parameter_id'):
    #         document_parameters_values = self.env['document.parameters'].search(
    #             [('parameter_id', 'in', document_parameters.ids)])
    #         if not document_parameters_values.selected_value_ids.ids:
    #             raise ValidationError("Please select a value for required document parameters before saving.")
    #     else:
    #         raise ValidationError("Parameter ID field is not defined in document.parameters model.")

        # for pv in parameter_values_access:
        #     if pv[0] == 0:
        #         if not pv[2].get("document_parameter_ids"):
        #             raise ValidationError("Please select a value for required document parameters before saving.")
        # if 'parameter_access' in pv[2]:
        #     selected_ids = pv[2]['parameter_access']
        #     if not set(selected_ids).intersection(document_parameter_ids):
        #         raise ValidationError("Selected values do not match any required document parameters.")

        return res
