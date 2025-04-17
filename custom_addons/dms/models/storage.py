
import logging
import os
from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from odoo.tools import config
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class Storage(models.Model):

    _name = "dms.storage"
    _description = "Storage"

    # ----------------------------------------------------------
    # Database
    # ----------------------------------------------------------

    name = fields.Char(required=True)

    save_type = fields.Selection(
        selection=[
            # ("database", _("Database")),
            ("file", _("Filestore")),
            # ("attachment", _("Attachment")),
        ],
        default="file",
        required=True,
        help="""The save type is used to determine how a file is saved by the
        system. If you change this setting, you can migrate existing files
        manually by triggering the action.""",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        help="If set, directories and files will only be available for "
        "the selected company.",
    )

    is_hidden = fields.Boolean(
        string="Storage is Hidden",
        default=False,
        help="Indicates if directories and files are hidden by default.",
    )

    root_directory_ids = fields.One2many(
        comodel_name="dms.directory",
        inverse_name="storage_id",
        string="Root Directories",
        auto_join=False,
        readonly=False,
        copy=False,
    )

    storage_directory_ids = fields.One2many(
        comodel_name="dms.directory",
        inverse_name="storage_id",
        string="Directories",
        auto_join=False,
        readonly=True,
        copy=False,
    )

    storage_file_ids = fields.One2many(
        comodel_name="dms.file",
        inverse_name="storage_id",
        string="Files",
        auto_join=False,
        readonly=True,
        copy=False,
    )

    count_storage_directories = fields.Integer(
        compute="_compute_count_storage_directories", string="Count Directories"
    )

    count_storage_files = fields.Integer(
        compute="_compute_count_storage_files", string="Count Files"
    )

    model_ids = fields.Many2many("ir.model", string="Linked Models")
    inherit_access_from_parent_record = fields.Boolean(
        string="Inherit permissions from related record",
        default=False,
        help="Indicate if directories and files access work only with "
        "related model access (for example, if some directories are related "
        "with any sale, only users with read access to these sale can acess)",
    )
    include_message_attachments = fields.Boolean(
        string="Create files from message attachments",
        default=False,
        help="Indicate if directories and files auto-create in mail "
        "composition process too",
    )
    model = fields.Char(search="_search_model", store=False)
    
    def _get_filestore_path(self):
        """
        Retrieve the filestore path for the current database.
        """
        db_name = self.env.cr.dbname
        base_filestore = os.path.join(config.filestore(self.env.cr.dbname))
        if not os.path.exists(base_filestore):
            raise UserError(f"Filestore path does not exist: {base_filestore}")
        return base_filestore
    
    url = fields.Char(string="Filestore Url", default=lambda self: self._get_filestore_path())
    
    @api.constrains('url')
    def _check_url_validity(self):
        """
        Validate that the URL is not empty and corresponds to a valid directory in the system.
        """
        for record in self:
            if not record.url:
                raise ValidationError("The filestore URL cannot be empty.")
            if not os.path.exists(record.url):
                raise ValidationError(f"The specified filestore path does not exist: {record.url}")
            if not os.path.isdir(record.url):
                raise ValidationError(f"The specified filestore path is not a directory: {record.url}")

    def _search_model(self, operator, value):
        allowed_items = self.env["ir.model"].sudo().search([("model", operator, value)])
        return [("model_ids", "in", allowed_items.ids)]

    @api.onchange("save_type")
    def _onchange_save_type(self):
        for record in self:
            if record.save_type == "attachment":
                record.inherit_access_from_parent_record = True

    # ----------------------------------------------------------
    # Actions
    # ----------------------------------------------------------

    def action_storage_migrate(self):
        if self.save_type != "attachment":
            if not self.env.user.has_group("dms.group_dms_manager"):
                raise AccessError(_("Only managers can execute this action."))
            files = self.env["dms.file"].with_context(active_test=False).sudo()

            for record in self:
                domain = [
                    ("require_migration", "=", True),
                    ("storage_id", "=", record.id),
                ]
                files.search(domain).action_migrate()

    def action_save_onboarding_storage_step(self):
        self.env.user.company_id.set_onboarding_step_done(
            "documents_onboarding_storage_state"
        )

    # ----------------------------------------------------------
    # Read, View
    # ----------------------------------------------------------

    @api.depends("storage_directory_ids")
    def _compute_count_storage_directories(self):
        for record in self:
            record.count_storage_directories = len(record.storage_directory_ids)

    @api.depends("storage_file_ids")
    def _compute_count_storage_files(self):
        for record in self:
            record.count_storage_files = len(record.storage_file_ids)
