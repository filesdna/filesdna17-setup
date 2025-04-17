from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # ✅ File Upload Settings
    documents_binary_max_size = fields.Integer(
        string="Size",
        help="Defines the maximum upload size in MB. Default (25MB).",
        config_parameter="dms.binary_max_size",
    )

    documents_forbidden_extensions = fields.Char(
        string="Extensions",
        help="Defines a list of forbidden file extensions. (Example: 'exe,msi').",
        config_parameter="dms.forbidden_extensions",
    )

    # ✅ Directory Management
    enable_directory_creation = fields.Boolean(
        string="Enable Template Directory Structure Creation",
        config_parameter="dms.enable_directory_creation",
        help="When enabled, files will automatically create directories based on unit, in/out type, and year.",
    )

    directory_template_id = fields.Many2one(
        "dms.directory.template",
        string="Default Directory Template",
        config_parameter="dms.directory_template_id",
        help="Select a default template to apply when creating directories.",
    )

    filter_tags = fields.Many2many(
        "dms.tag",
        "res_config_settings_dms_tag_rel",
        "config_id",
        "tag_id",
        string="Document Tags",
    )

    get_employee_documents = fields.Boolean(
        string="Enable Employee Document Filtering",
        config_parameter="dms.get_employee_documents",
    )

    enable_auto_tagging = fields.Boolean(
        string="Enable Auto Tagging",
        help="Automatically tag uploaded files with the group name and user email",
        config_parameter="dms.enable_auto_tagging",
    )
    enable_document_filter = fields.Boolean(
        string="Enable Document Filter",
        config_parameter="dms.enable_document_filter",
        help="When enabled, the Document Parameters menu will be shown.",
    )

    @api.onchange('enable_document_filter')
    def show_document_filter(self):
        group_enable_document_filter = self.env.ref('dms.group_show_document_parameters', raise_if_not_found=False)
        print('enable_document_filter=', self.enable_document_filter)
        print('enable_document_filter_group=', group_enable_document_filter.name)

        # Get all groups, files, and users once
        groups = self.env['dms.access.group'].search([])
        files = self.env['dms.file'].search([])
        users = self.env['res.users'].search([])

        # Update the enable_document_filter for groups and files
        groups.write({"enable_document_filter": self.enable_document_filter})
        files.write({"enable_document_filter": self.enable_document_filter})

        # Update user groups based on the enable_document_filter
        for user in users:
            print('user_enable=', user.name)
            if self.enable_document_filter:
                if group_enable_document_filter not in user.groups_id:
                    user.groups_id = [(4, group_enable_document_filter.id)]
            else:
                if group_enable_document_filter in user.groups_id:
                    user.groups_id = [(3, group_enable_document_filter.id)]

        # Print updated states for debugging
        for group in groups:
            print('group_enable=', group.name, 'enable_document_filter=', group.enable_document_filter)
        for file in files:
            print('file_enable=', file.name, 'enable_document_filter=', file.enable_document_filter)

    @api.model
    def get_values(self):
        """ Load stored settings from config parameters. """
        res = super().get_values()
        params = self.env["ir.config_parameter"].sudo()

        tag_names = params.get_param("dms.filter_tags", default="")
        tag_ids = self.env["dms.tag"].search([("name", "in", tag_names.split(","))]).ids if tag_names else []

        res.update({
            "enable_directory_creation": params.get_param("dms.enable_directory_creation", default="False") == "True",
            "directory_template_id": int(params.get_param("dms.directory_template_id", default=False)) or False,
            "filter_tags": [(6, 0, tag_ids)] if tag_ids else [],
            "get_employee_documents": params.get_param("dms.get_employee_documents", default="False") == "True",
            "enable_auto_tagging": params.get_param("dms.enable_auto_tagging", default="False") == "True",  # ✅ added
            "enable_document_filter": params.get_param("dms.enable_document_filter", default="False") == "True",
        })
        return res

    def set_values(self):
        """ Save user-configured values to config parameters. """
        super().set_values()
        params = self.env["ir.config_parameter"].sudo()

        params.set_param("dms.enable_directory_creation", self.enable_directory_creation)
        params.set_param("dms.directory_template_id",
                         self.directory_template_id.id if self.directory_template_id else False)
        params.set_param("dms.filter_tags", ",".join(self.filter_tags.mapped("name")) if self.filter_tags else "")
        params.set_param("dms.get_employee_documents", "True" if self.get_employee_documents else "False")
        params.set_param("dms.enable_auto_tagging", "True" if self.enable_auto_tagging else "False")  # ✅ added
        params.set_param("dms.enable_document_filter", "True" if self.enable_document_filter else "False")
