from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import requests
import base64
import json
import logging
from collections import defaultdict
import binascii
from PIL import Image
import time
from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError,UserError
from odoo.osv import expression
from odoo.tools import consteq, human_size
from odoo.tools.mimetypes import guess_mimetype
import hashlib
from cryptography.fernet import Fernet
from odoo.http import request
from google.cloud import storage
from google.oauth2 import service_account
from ..tools import file
import os
from odoo.tools import config
import shutil
import re

google_bucket = config['google_bucket']
_logger = logging.getLogger(__name__)

class File(models.Model):
    _name = "dms.file"
    _description = "File"

    _inherit = [
        "portal.mixin",
        "dms.security.mixin",
        "dms.mixins.thumbnail",
        "mail.thread",
        "mail.activity.mixin",
        "abstract.dms.mixin",
    ]

    _order = "name asc"

    # ----------------------------------------------------------
    # Database
    # ----------------------------------------------------------
    active = fields.Boolean(
        string="Archived",
        default=True,
        help="If a file is set to archived, it is not displayed, but still exists.")
    is_deleted = fields.Boolean(
        string="Deleted",
        default=False,
        help="If a file is set to archived, it is not displayed, but still exists.")
    directory_id = fields.Many2one(
        comodel_name="dms.directory",
        string="Directory",
        ondelete="restrict",
        auto_join=True,
        required=True,
        index=True)
    directories_ids = fields.Many2many('dms.directory', string='Directory Filter',compute='_compute_directories_ids')
    old_directory_id = fields.Many2one(
        comodel_name="dms.directory",
        string="Old Directory")
    storage_id = fields.Many2one(
        related="directory_id.storage_id",
        readonly=True,
        store=True,
        prefetch=False)
    current_time_seconds = fields.Integer(string="Current Time Seconds")
    path_names = fields.Char(
        compute="_compute_path",
        compute_sudo=True,
        readonly=True,
        store=False)
    path_json = fields.Text(
        compute="_compute_path",
        compute_sudo=True,
        readonly=True,
        store=False)
    tag_ids = fields.Many2many(
        comodel_name="dms.tag",
        relation="dms_file_tag_rel",
        column1="fid",
        column2="tid",
        domain="['|', ('category_id', '=', False),('category_id', '=?', category_id)]",
        string="Tags")
    decripted_content = fields.Binary(store=True)
    encripted_content = fields.Binary(store=True)
    content = fields.Binary(
        compute="_compute_content",
        inverse="_inverse_content",
        attachment=False,
        prefetch=False,
        required=True,
        store=False)
    document_status = fields.Selection(string='Status', selection=[('Draft', 'Draft'), 
    ('Pending', 'Pending'),
    ('in_process', 'In Process'),
    ('Preparing', 'Preparing'),
    ('Completed', 'Completed'),
    ('pending_owner', 'Pending Owner'),
    ('Declined', 'Declined'),
    ], default='Draft',readonly=True)
    extension = fields.Char(compute="_compute_extension", readonly=True, store=True)
    mimetype = fields.Char(compute="_compute_mimetype", string="Type", readonly=True, store=True)
    size = fields.Float(readonly=True)
    human_size = fields.Char(readonly=True, string="Size", compute="_compute_human_size", store=True)
    checksum = fields.Char(string="Checksum/SHA1", readonly=True, index=True)
    content_binary = fields.Binary(attachment=False, prefetch=False, invisible=True)
    save_type = fields.Char(
        compute="_compute_save_type",
        string="Current Save Type",
        invisible=True,
        prefetch=False)
    migration = fields.Char(
        compute="_compute_migration",
        string="Migration Status",
        readonly=True,
        prefetch=False,
        compute_sudo=True)
    require_migration = fields.Boolean(compute="_compute_migration", store=False, compute_sudo=True)
    content_file = fields.Binary(attachment=True, prefetch=False, invisible=True)
    # Extend inherited field(s)
    image_1920 = fields.Image(compute="_compute_image_1920", store=True, readonly=False, max_width=128, max_height=128)
    metadata_configuration_id = fields.Many2one(comodel_name='metadata.configuration', string='Meta Data Category')
    has_summary = fields.Selection(related="metadata_configuration_id.has_summary")
    has_notes = fields.Selection(related="metadata_configuration_id.has_notes")
    summary =  fields.Html('Summary')
    notes =  fields.Text('Notes')
    linked_fiels_ids = fields.One2many(comodel_name='dms.file.line', inverse_name='parent_file_id', string='Linked Files')
    linked_fiels = fields.Integer(compute='compute_linked_fiels', store=True, default=0, readonly=True, string='Linked Files')
    #SHA-512 Hash
    sha512_hash = fields.Char(string='SHA-512 Hash', readonly=True)
    current_version_id = fields.Many2one('document.version', string='Current Version')
    document_versions_ids = fields.One2many(comodel_name='document.version', inverse_name='document_id', string='Document Versions')
    encription_user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    encription_key = fields.Char(string='Encription Key', related='encription_user_id.encription_key', readonly=True, store=True)
    
    # ---------------------- added fields -----------------------------------------
    is_template = fields.Boolean(string = "Is template", default = False)
    is_uploaded = fields.Boolean(string = "Is uploaded?", default = False)
    document_model = fields.Selection([
        ('normal', 'Normal'),
        ('crm', 'CRM'),
        ('itrack', 'iTrack'),
        ('matter', 'Matter'),
        ],default='normal')

    owner_lock = fields.Boolean(
        string="Locked By Owner",
        default=False,
        track_visibility='onchange'
    )
   


    @api.onchange('name')
    def onchange_name(self):
        if self.directory_id:
            groups = self.directory_id.complete_group_ids.ids
            self.has_permission(groups_ids=groups, permission='perm_rename')

    def write(self, vals):
        if self.directory_id:
            groups = self.directory_id.complete_group_ids.ids
            self.has_permission(groups_ids=groups, permission='perm_write')
        
        if 'attachment_ids' in vals and vals['attachment_ids']:
            self._create_new_version(vals['attachment_ids'])           
        return super(File, self).write(vals)
        
    def create_document_version(self, document_name, document_id, data):
        _logger.info(f"Datas:::{data}")
        base64_string = data.decode('utf-8')
        _logger.info(f"Base64:::{base64_string}")
        sha512_hash = self.generate_sha512(data)
        new_version_vals = {
            'name': document_name,
            'document_id': document_id,
            'file_data': data,
            'sha512_hash': sha512_hash,
            
        }
        _logger.info(f"content::{data}")
        document_version = self.env['document.version'].create(new_version_vals)
        self.sha512_hash = sha512_hash
        self.current_version_id = document_version.id
        attachment = (
            self.env["ir.attachment"]
            .create(
                {
                    "name": document_name,
                    "datas": data,
                    "res_model": 'document.version',
                    "res_id":  document_version.id,
                }
            )
        )
        document_version.write({'attachment_id' : attachment.id,
                                    'attachment_ids': [(6, 0, attachment.ids)]})
        
        user = self.env['res.users'].search([('id','=',self.env.user.id)])
        if user and self.extension == "pdf" and not self.is_uploaded:
            fname = attachment.store_fname
            current_time_seconds = time.time()
            current_time_milliseconds = int(current_time_seconds)
            self.current_time_seconds = current_time_milliseconds
        # //////////////////////////////// create elastic index /////////////////////////////////
        company_name = self.env.user.company_id.name
        self.create_elastic_index(company_name,self.id,document_name,base64_string)


    def _create_new_version(self, new_attachment_ids):
        if new_attachment_ids:
            for attachment_id in new_attachment_ids:
                if attachment_id:
                    attachment = attachment_id if isinstance(attachment_id, int) else attachment_id[-1] if isinstance(attachment_id, list) else None
                    if attachment:
                        attachment_obj = self.env['ir.attachment'].search([('id', '=', attachment)], limit=1)
                        if attachment_obj:
                            attachment_ids = attachment_obj.ids if isinstance(attachment_obj.ids, list) else [attachment_obj.ids]
                            self.attachment_ids = [(6, 0, attachment_ids)]
                            self.create_document_version(document_name=self.attachment_ids[0].name, document_id=self.id, data=self.attachment_ids[0].datas)
                            self.save_encrypted_file(self.attachment_ids[0].datas, '/opt/filesdna17/custom_addons/encrypted_image.enc')
                            self.name = self.attachment_ids[0].name
                            last_record = self.current_version_id
                            last_record[-1:].current_time_seconds = self.current_time_seconds
                            image = self.attachment_ids[0].mimetype.split("/")[0]
                            if image == 'image':
                                self.image_1920 = self.attachment_ids[0].datas
                            # else:
                            #     self.image_1920 = False

    @api.depends("linked_fiels_ids")
    def compute_linked_fiels(self):
        for rec in self:
            rec.linked_fiels = len(rec.linked_fiels_ids)

    @api.depends("mimetype", "content")
    def _compute_image_1920(self):
        """Provide thumbnail automatically if possible."""
        for one in self.filtered("mimetype"):
            # Image.MIME provides a dict of mimetypes supported by Pillow,
            # SVG is not present in the dict but is also a supported image format
            # lacking a better solution, it's being added manually
            # Some component modifies the PIL dictionary by adding PDF as a valid
            # image type, so it must be explicitly excluded.
            if one.mimetype != "application/pdf" and one.mimetype in (
                *Image.MIME.values(),
                "image/svg+xml",
            ):
                one.image_1920 = one.content

    def check_access_rule(self, operation):
        self.mapped("directory_id").check_access_rule(operation)
        return super().check_access_rule(operation)

    def _compute_access_url(self):
        res = super()._compute_access_url()
        for item in self:
            item.access_url = "/my/dms/file/%s/download" % (item.id)
        return res

    def check_access_token(self, access_token=False):
        res = False
        if access_token:
            if self.access_token and consteq(self.access_token, access_token):
                return True
            else:
                items = (
                    self.env["dms.directory"]
                    .sudo()
                    .search([("access_token", "=", access_token)])
                )
                if items:
                    item = items[0]
                    if self.directory_id.id == item.id:
                        return True
                    else:
                        directory_item = self.directory_id
                        while directory_item.parent_id:
                            if directory_item.id == self.directory_id.id:
                                return True
                            directory_item = directory_item.parent_id
                        # Fix last level
                        if directory_item.id == self.directory_id.id:
                            return True
        return res

    res_model = fields.Char(
        string="Linked attachments model", related="directory_id.res_model"
    )
    res_id = fields.Integer(
        string="Linked attachments record ID", related="directory_id.res_id"
    )
    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Attachment File",
        prefetch=False,
        invisible=True,
        ondelete="cascade",
    )
    decrypted_attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Attachment File",
        prefetch=False,
        invisible=True,
        ondelete="cascade",
    )
    attachment_ids = fields.Many2many('ir.attachment', string="Upload New Version")
    decrypted_attachment_ids = fields.Many2many('ir.attachment', string="Content",
                                                relation="decrypted_file_rel",
        column1="fid",
        column2="decript_id",)
    is_encrypted = fields.Boolean()
    is_decrypted = fields.Boolean()
    is_renamed = fields.Boolean()
    
    @api.model
    def has_permission(self, groups_ids, permission):
        """
        Check if the current user has the specified permission in at least one group.
        
        :param permission: The permission to check (e.g., 'create', 'download', 'edit', 'delete').
        :return: True if the user has the permission in at least one group, False otherwise.
        """
        user = self.env.user
        groups_with_permission = self.env['dms.access.group'].search([('id', 'in', groups_ids), (permission, '=', True)])
        if groups_with_permission:
            for group in groups_with_permission:
                if user.id in group.users.ids:
                    return True
        else:
            if permission == 'perm_create':
                raise ValidationError("You do not have permission to create this record.")
            if permission == 'perm_download':
                raise ValidationError("You do not have permission to download this record.")
            if permission == 'perm_unlink':
                raise ValidationError("You do not have permission to delete this record.")
            if permission == 'perm_write':
                raise ValidationError("You do not have permission to edit this record.")
            if permission == 'perm_rename':
                raise ValidationError("You do not have permission to rename this record.")
            if permission == 'perm_lock':
                raise ValidationError("You do not have lock permission on this record.")

    def get_human_size(self):
        return human_size(self.size)

    # ----------------------------------------------------------
    # Helper
    # ----------------------------------------------------------

    @api.model
    def _get_checksum(self, binary):
        return hashlib.sha1(binary or b"").hexdigest()

    @api.model
    def _get_content_inital_vals(self):
        return {"content_binary": False, "content_file": False}

    def _update_content_vals(self, vals, binary):
        new_vals = vals.copy()
        new_vals.update(
            {
                "checksum": self._get_checksum(binary),
                "size": binary and len(binary) or 0,
            }
        )
        if self.storage_id.save_type in ["file", "attachment"]:
            new_vals["content_file"] = self.content
        else:
            new_vals["content_binary"] = self.content and binary
        return new_vals

    @api.model
    def _get_binary_max_size(self):
        return int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("dms.binary_max_size", default=25)
        )

    @api.model
    def _get_forbidden_extensions(self):
        get_param = self.env["ir.config_parameter"].sudo().get_param
        extensions = get_param("dms.forbidden_extensions", default="")
        return [extension.strip() for extension in extensions.split(",")]

    def _get_icon_placeholder_name(self):
        return self.extension and "file_%s.svg" % self.extension or ""

    # ----------------------------------------------------------
    # Actions
    # ----------------------------------------------------------

    def action_migrate(self, logging=True):
        record_count = len(self)
        index = 1
        for dms_file in self:
            if logging:
                _logger.info(
                    _(
                        "Migrate File %(index)s of %(record_count)s [ %(dms_file_migration)s ]"
                    )
                    % {
                        "index": index,
                        "record_count": record_count,
                        "dms_file_migration": dms_file.migration,
                    }
                )
                index += 1
            dms_file.write({"content": dms_file.with_context(**{}).content})

    def action_save_onboarding_file_step(self):
        self.env.user.company_id.set_onboarding_step_done(
            "documents_onboarding_file_state"
        )

    # ----------------------------------------------------------
    # SearchPanel
    # ----------------------------------------------------------

    @api.model
    def _search_panel_directory(self, **kwargs):
        search_domain = (kwargs.get("search_domain", []),)
        category_domain = kwargs.get("category_domain", [])
        if category_domain and len(category_domain):
            return "=", category_domain[0][2]
        if search_domain and len(search_domain):
            for domain in search_domain[0]:
                if domain[0] == "directory_id":
                    return domain[1], domain[2]
        return None, None

    @api.model
    def _search_panel_domain(self, field, operator, directory_id, comodel_domain=False):
        if not comodel_domain:
            comodel_domain = []
        files_ids = self.search([("directory_id", operator, directory_id)]).ids
        return expression.AND([comodel_domain, [(field, "in", files_ids)]])

    @api.model
    def search_panel_select_range(self, field_name, **kwargs):
        """This method is overwritten to make it 'similar' to v13.
        The goal is that the directory searchpanel shows all directories
        (even if some folders have no files)."""
        
        if field_name == "directory_id":
            domain = [["is_hidden", "=", False]]
            # If we pass by context something, we filter more about it we filter
            # the directories of the files or we show all of them
            if self.env.context.get("active_model", False) == "dms.directory":
                active_id = self.env.context.get("active_id")
                files = self.env["dms.file"].search(
                    [["directory_id", "child_of", active_id]]
                )
                all_directories = files.mapped("directory_id")
                all_directories += files.mapped("directory_id.parent_id")
                domain.append(["id", "in", all_directories.ids])
            # Get all possible directories
            comodel_records = (
                self.env["dms.directory"]
                .with_context(directory_short_name=True)
                .search_read(domain, ["display_name", "parent_id"])
            )
            all_record_ids = [rec["id"] for rec in comodel_records]
            field_range = {}
            enable_counters = kwargs.get("enable_counters")
            for record in comodel_records:
                record_id = record["id"]
                parent = record["parent_id"]
                record_values = {
                    "id": record_id,
                    "display_name": record["display_name"],
                    # If the parent directory is not in all the records we should not
                    # set parent_id because the user does not have access to parent.
                    "parent_id": (
                        parent[0] if parent and parent[0] in all_record_ids else False
                    ),
                }
                if enable_counters:
                    record_values["__count"] = 0
                field_range[record_id] = record_values
            if enable_counters:
                res = super().search_panel_select_range(field_name, **kwargs)
                for item in res["values"]:
                    field_range[item["id"]]["__count"] = item["__count"]
            return {"parent_field": "parent_id", "values": list(field_range.values())}
        context = {}
        if field_name == "category_id":
            context["category_short_name"] = True
        return super(File, self.with_context(**context)).search_panel_select_range(
            field_name, **kwargs
        )
    
    # ------- Zenab -------------
    @api.model
    def get_directory_for_panel(self, directory_id):
        directory = self.env['dms.directory'].sudo().search([('id','=',int(directory_id))])
        if directory.dms_security_id.selection == 'g2fa' and directory.active_security:
            return True
        else:
            return False

    @api.model
    def search_panel_select_multi_range(self, field_name, **kwargs):
        operator, directory_id = self._search_panel_directory(**kwargs)
        if field_name == "tag_ids":
            sql_query = """
                SELECT t.name AS name, t.id AS id, c.name AS group_name,
                    c.id AS group_id, COUNT(r.fid) AS count
                FROM dms_tag t
                JOIN dms_category c ON t.category_id = c.id
                LEFT JOIN dms_file_tag_rel r ON t.id = r.tid
                WHERE %(filter_by_file_ids)s IS FALSE OR r.fid = ANY(%(file_ids)s)
                GROUP BY c.name, c.id, t.name, t.id
                ORDER BY c.name, c.id, t.name, t.id;
            """
            file_ids = []
            if directory_id:
                file_ids = self.search([("directory_id", operator, directory_id)]).ids
            self.env.cr.execute(
                sql_query,
                {"file_ids": file_ids, "filter_by_file_ids": bool(directory_id)},
            )
            return self.env.cr.dictfetchall()
        if directory_id and field_name in ["directory_id", "category_id"]:
            comodel_domain = kwargs.pop("comodel_domain", [])
            directory_comodel_domain = self._search_panel_domain(
                "file_ids", operator, directory_id, comodel_domain
            )
            return super(
                File, self.with_context(directory_short_name=True)
            ).search_panel_select_multi_range(
                field_name, comodel_domain=directory_comodel_domain, **kwargs
            )
        return super(
            File, self.with_context(directory_short_name=True)
        ).search_panel_select_multi_range(field_name, **kwargs)

    # ----------------------------------------------------------
    # Read
    # ----------------------------------------------------------

    @api.depends("name", "directory_id", "directory_id.parent_path")
    def _compute_path(self):
        model = self.env["dms.directory"]
        for record in self:
            if record.display_name:
                path_names = [record.display_name]
            else:
                path_names = []

            path_json = [
                {
                    "model": record._name,
                    "name": record.display_name,
                    "id": isinstance(record.id, int) and record.id or 0,
                }
            ]
            current_dir = record.directory_id
            while current_dir:
                path_names.insert(0, current_dir.name)
                path_json.insert(
                    0,
                    {
                        "model": model._name,
                        "name": current_dir.name,
                        "id": current_dir._origin.id,
                    },
                )
                current_dir = current_dir.parent_id
            record.update(
                {
                    "path_names": "/".join(path_names),
                    "path_json": json.dumps(path_json),
                }
            )

    @api.depends("name", "mimetype", "content")
    def _compute_extension(self):
        for record in self:
            record.extension = file.guess_extension(
                record.name, record.mimetype, record.content
            )
            file_extension = record.extension
            company_image = record.env['res.company.dms'].search([('file_extension','=',file_extension)],
                    limit=1
                ) 
            if company_image:
                try:
                    # Ensure the image is in base64 format before assigning
                    base64.b64decode(company_image.file_image)
                    record.image_1920 = company_image.file_image
                except base64.binascii.Error:
                    _logger.warning(f"File image for {company_image} is not properly encoded in base64.")
            

    @api.depends("content")
    def _compute_mimetype(self):
        for record in self:
            if record.content:
                try:
                    # Ensure proper padding before decoding
                    padded_content = record.content + b'=' * ((4 - len(record.content) % 4) % 4)
                    binary = base64.b64decode(padded_content)
                    record.mimetype = guess_mimetype(binary)
                except binascii.Error:
                    # Handle the error appropriately, perhaps by setting mimetype to None or logging the issue
                    record.mimetype = None

    @api.depends("size")
    def _compute_human_size(self):
        for item in self:
            item.human_size = human_size(item.size)

    @api.depends("content_binary", "content_file", "attachment_id")
    def _compute_content(self):
        bin_size = self.env.context.get("bin_size", False)
        for record in self:
            if record.content_file:
                context = {"human_size": True} if bin_size else {"base64": True}
                record.content = record.with_context(**context).content_file
            elif record.content_binary:
                record.content = (
                    record.content_binary
                    if bin_size
                    else base64.b64encode(record.content_binary)
                )
            elif record.attachment_id:
                context = {"human_size": True} if bin_size else {"base64": True}
                record.content = record.with_context(**context).attachment_id.datas

    @api.depends("content_binary", "content_file")
    def _compute_save_type(self):
        for record in self:
            if record.content_file:
                record.save_type = "file"
            else:
                record.save_type = "database"

    @api.depends("storage_id", "storage_id.save_type")
    def _compute_migration(self):
        storage_model = self.env["dms.storage"]
        save_field = storage_model._fields["save_type"]
        values = save_field._description_selection(self.env)
        selection = {value[0]: value[1] for value in values}
        for record in self:
            storage_type = record.storage_id.save_type
            if storage_type == "attachment" or storage_type == record.save_type:
                record.migration = selection.get(storage_type)
                record.require_migration = False
            else:
                storage_label = selection.get(storage_type)
                file_label = selection.get(record.save_type)
                record.migration = "{} > {}".format(file_label, storage_label)
                record.require_migration = True

    # ----------------------------------------------------------
    # View
    # ----------------------------------------------------------

    @api.onchange("category_id")
    def _change_category(self):
        self.tag_ids = self.tag_ids.filtered(
            lambda rec: not rec.category_id or rec.category_id == self.category_id
        )

    # ----------------------------------------------------------
    # Constrains
    # ----------------------------------------------------------

    @api.constrains("storage_id", "res_model", "res_id")
    def _check_storage_id_attachment_res_model(self):
        for record in self:
            if record.storage_id.save_type == "attachment" and not (
                record.res_model and record.res_id
            ):
                raise ValidationError(
                    _("A file must have model and resource ID in attachment storage.")
                )

    @api.constrains("extension")
    def _check_extension(self):
        for record in self:
            if (
                record.extension
                and record.extension in self._get_forbidden_extensions()
            ):
                raise ValidationError(_("The file has a forbidden file extension."))

    @api.constrains("size")
    def _check_size(self):
        for record in self:
            if record.size and record.size > self._get_binary_max_size() * 1024 * 1024:
                raise ValidationError(
                    _("The maximum upload size is %s MB).")
                    % self._get_binary_max_size()
                )

    # ----------------------------------------------------------
    # Create, Update, Delete
    # ----------------------------------------------------------

    def _inverse_content(self):
        pass

    def _create_model_attachment(self, vals):
        res_vals = vals.copy()
        if "directory_id" in res_vals:
            directory_id = res_vals["directory_id"]
        elif self.env.context.get("active_id"):
            directory_id = self.env.context.get("active_id")
        elif self.env.context.get("default_directory_id"):
            directory_id = self.env.context.get("default_directory_id")
        directory = self.env["dms.directory"].browse(directory_id)
        attachment = (
            self.env["ir.attachment"]
            .create(
                {
                    "name": vals["name"],
                    "datas": vals["content"],
                    "res_model": 'dms.file',
                    "res_id":  vals.get('id'),
                }
            )
        )

        res_vals["attachment_id"] = attachment.id
        return res_vals

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or [])
        if "directory_id" in default:
            model = self.env["dms.directory"]
            directory = model.browse(default["directory_id"])
            names = directory.sudo().file_ids.mapped("name")
        else:
            names = self.sudo().directory_id.file_ids.mapped("name")
        default.update({"name": file.unique_name(self.name, names, self.extension)})
        return super(File, self).copy(default)
    
    def save_encrypted_file(self, encrypted_content, file_path):
        with open(file_path, 'wb') as file:
            file.write(encrypted_content)

    def load_encrypted_image(self, file_path):
        with open(file_path, 'rb') as file:
            encrypted_content = file.read()
        return encrypted_content
    
    @api.model
    def action_delete(self):
        for rec in self:
            rec.unlink_file()

    def decrypt_document_version_content(self, content):
        last_record = self.document_versions_ids.sorted('id', reverse=True)[0]
        if last_record:
            attachment_records = last_record.attachment_ids
            attachment_records.write({'datas': content})
    
    def _get_key_from_company(self):
        encryption_key = self.env.user.company_id.encription_key
        # encoded_key = encryption_key.encode('utf-8')
        # hex_key = encoded_key
        # bytes_key = bytes.fromhex(hex_key.decode())
        # base64_key = base64.urlsafe_b64encode(bytes_key)
        return encryption_key

    def compute_sha512_hash(self,file_path):
        """Compute the SHA-512 hash of a file."""
        hash_sha512 = hashlib.sha512()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha512.update(chunk)
        
        return hash_sha512.hexdigest()

    def _encrypt_content(self, file_path, is_unlocked=None):
        try:
            base64_key = self._get_key_from_company()  # Retrieve the base64-encoded key from the company
            cipher = Fernet(base64_key)  # Initialize the cipher using the key

            # Compute original file hash
            original_hash = self.compute_sha512_hash(file_path)
            _logger.info(f"Original file SHA-512 hash before encryption: {original_hash}")

            # Read the original file content
            with open(file_path, 'rb') as f:
                file_data = f.read()

            # Encrypt the file data
            encrypted_data = cipher.encrypt(file_data)

            # Overwrite the original file with the encrypted content
            with open(file_path, 'wb') as f:
                f.write(encrypted_data)

            # Compute the hash of the encrypted file
            encrypted_hash = self.compute_sha512_hash(file_path)
            _logger.info(f"Encrypted file SHA-512 hash: {encrypted_hash}")

            return file_path
        except UnicodeDecodeError:
            _logger.error("Error: Non-UTF-8 encoded content")
            return "Error: Non-UTF-8 encoded content"

    def decrypt_content(self, encrypted_file_path):
        base64_key = self._get_key_from_company()  # Retrieve the base64-encoded key
        cipher = Fernet(base64_key)

        # Compute hash of encrypted file before decryption
        encrypted_hash = self.compute_sha512_hash(encrypted_file_path)
        _logger.info(f"Encrypted file SHA-512 hash before decryption: {encrypted_hash}")

        # Read the encrypted file content
        with open(encrypted_file_path, 'rb') as f:
            encrypted_data = f.read()

        # Decrypt the data
        decrypted_data = cipher.decrypt(encrypted_data)

        # Overwrite the encrypted file with the decrypted content
        with open(encrypted_file_path, 'wb') as f:
            f.write(decrypted_data)

        # Compute the hash of the decrypted file
        decrypted_hash = self.compute_sha512_hash(encrypted_file_path)
        _logger.info(f"Decrypted file SHA-512 hash: {decrypted_hash}")

        return encrypted_file_path

    def get_storage_client(self):
        credentials = service_account.Credentials.from_service_account_file(f"/opt/filesdna17/custom_addons/google_cloud_storage/google_creds.json")
        storage_client = storage.Client(credentials=credentials)
        return storage_client

    def _download_from_google_bucket(self, bucket_name, file_path, fname):
        """Download the file from Google Cloud Bucket to the local system."""
        try:
            # Define the local path where the file will be stored
            local_path = f"/opt/filesdna17/custom_addons/temp-folder/{fname}"

            # Get the directory part of the local path
            local_dir = os.path.dirname(local_path)

            # Ensure the local directory exists
            if not os.path.exists(local_dir):
                os.makedirs(local_dir, exist_ok=True)  # Create the directory if it doesn't exist

            # Download the file from Google Bucket
            storage_client = self.get_storage_client()
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(file_path)
            blob.download_to_filename(local_path)

            _logger.info(f"File downloaded to: {local_path}")
            return local_path

        except Exception as e:
            _logger.error(f"Error downloading file from Google Bucket: {e}")
            raise


    def _upload_to_google_bucket(self, bucket_name, file_path, destination_blob_name):
        """Upload file to Google Cloud Storage."""
        try:
            # Ensure the local file exists before attempting the upload
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File '{file_path}' does not exist locally for upload.")
            
            # Initialize the Google Cloud Storage client
            storage_client = self.get_storage_client()
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(destination_blob_name)

            # Upload the file to the bucket
            blob.upload_from_filename(file_path)

            _logger.info(f"File '{file_path}' successfully uploaded to '{bucket_name}/{destination_blob_name}'")
            return True

        except Exception as e:
            _logger.error(f"Error during upload: {e}")
            raise

    def _delete_from_google_bucket(self, bucket_name, file_path):
        storage_client = self.get_storage_client()
        bucket = storage_client.get_bucket(bucket_name)
        blob = bucket.blob(file_path)
        blob.delete()
        _logger.info(f"Deleted {file_path} from bucket {bucket_name}")
        
        
    def generate_sha512(self, content):
        file_data_bytes = base64.b64decode(content)
        sha512_hash = hashlib.sha512(file_data_bytes).hexdigest()
        return sha512_hash
        
    @api.model_create_multi
    def create(self, vals_list):
        new_vals_list = []
        for vals in vals_list:
            current_time_seconds = time.time()
            current_time_milliseconds = int(current_time_seconds)
            file_name = vals["name"]
            directory = self.env['dms.directory'].browse(vals.get('directory_id'))
            groups = directory.complete_group_ids.ids
            self.has_permission(groups_ids=groups, permission='perm_create')
            # SHA-512 hash for file content
            if vals.get('content'):
                file_data = vals['content']
                sha512_hash = self.generate_sha512(file_data)
                vals['sha512_hash'] = sha512_hash
            new_record = self._create_model_attachment(vals)
            new_vals_list.append(new_record)
        created_records = super(File, self).create(new_vals_list)
        for record in created_records:
            record.attachment_id.res_id = record.id
            record.attachment_ids = record.attachment_id.ids
            fname = record.attachment_ids.store_fname
            file_id = record.id

        user = self.env['res.users'].search([('id','=',self.env.user.id)])
        if user and self.extension == "pdf"and not self.is_uploaded:
            for record in created_records :
                record.current_time_seconds = current_time_milliseconds

        if self.env.user.is_auto_lock == True:
            record.lock()
        return created_records
    # ----------------------------------------------------------
    # Locking fields and functions
    # ----------------------------------------------------------

    locked_by = fields.Many2one(comodel_name="res.users")

    is_locked = fields.Boolean(compute="_compute_locked", string="Locked")

    is_lock_editor = fields.Boolean(compute="_compute_locked", string="Editor")

    # ----------------------------------------------------------
    # Locking
    # ----------------------------------------------------------
    
    @api.model
    def action_restore_multiple_files(self):
        for rec in self:
            rec.action_restore_file()

    def action_restore_file(self):
        self.is_deleted = False
        if self.directory_id.is_deleted == True:
            raise ValidationError(f"Please Restore Directory: {self.directory_id.name} First !")
        else:
            return {
                    'type': 'ir.actions.act_window',
                    'name': _ ('Files'),  
                    'view_type': 'kanban',
                    'view_mode': 'kanban,tree,form',
                    'res_model': 'dms.file',
                    'domain': [('is_deleted', '=', False)],
                    'target': 'main',
                } 

    def unlink_file(self):
        """Cascade DMS related resources removal.
        Avoid executing in ir.* models (ir.mode, ir.model.fields, etc), in transient
        models and in the models we want to check."""
        if self.id != False:
            if self.is_deleted == True:
                self.unlink()
            else:
                groups = self.directory_id.complete_group_ids.ids
                self.has_permission(groups_ids=groups, permission='perm_unlink')
                self.is_deleted = True

                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'kanban',
                    'name': _ ('Files'),  
                    'view_mode': 'kanban,tree,form',
                    'res_model': 'dms.file',
                    'domain': [('is_deleted', '=', True)],
                    'target': 'main',
                }

    def _check_upload_success(self, bucket_name, file_path):
        """
        Check if a file exists in Google Cloud Storage bucket after upload.

        Args:
        bucket_name (str): Name of the Google Cloud Storage bucket.
        file_path (str): Path to the file in the bucket.

        Returns:
        bool: True if the file exists in the bucket, False otherwise.
        """
        try:
            # Initialize Google Cloud Storage client
            storage_client = self.get_storage_client()
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(file_path)
            # Check if the blob exists
            if blob.exists():
                _logger.info(f"File '{file_path}' exists in the bucket '{bucket_name}'.")
                return True
            else:
                _logger.warning(f"File '{file_path}' does not exist in the bucket '{bucket_name}'.")
                return False
        except Exception as e:
            _logger.error(f"Error while checking file upload: {e}")
            return False

    def lock(self):
        if self.directory_id:
            try:
                fname = self.attachment_id.store_fname
                bucket = f"{google_bucket}"
                company_name = self.env.user.company_id.name
                db_name = request.env['ir.config_parameter'].sudo().get_param('web.base.url').split("//")[1].split(".")[0]
                file_path = f"{db_name}/{fname}"

                _logger.info(f"Starting lock process for file: {file_path}")

                groups = self.directory_id.complete_group_ids.ids
                self.has_permission(groups_ids=groups, permission='perm_lock')

                # Download file from Google Bucket to local storage
                local_file_path = self._download_from_google_bucket(bucket, file_path, fname)

                _logger.info(f"Downloaded file to local path: {local_file_path}")

                # Encrypt the downloaded file
                encrypted_content = self._encrypt_content(local_file_path, is_unlocked=False)

                _logger.info(f"File encrypted at local path: {encrypted_content}")

                # Ensure encryption success
                if not encrypted_content:
                    raise Exception("Encryption failed")

                # Upload the encrypted file back to Google Bucket
                self._upload_to_google_bucket(bucket, encrypted_content, f"{db_name}/{fname}")

                _logger.info(f"Uploaded encrypted file back to Google Bucket at {db_name}/{fname}")

                # Confirm upload success
                if not self._check_upload_success(bucket, f"{db_name}/{fname}"):
                    raise Exception("Failed to upload encrypted file to Google Bucket")

                # # Update the `datas` field with the base64-encoded encrypted file
                # with open(encrypted_content, 'rb') as file:
                #     encrypted_file_data = file.read()
                #     base64_encrypted_content = base64.b64encode(encrypted_file_data).decode('utf-8')


                self.write({"locked_by": self.env.uid, 'is_locked': True})
                self.locked_by_owner()

                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            except Exception as e:
                _logger.error(f"Error during lock: {e}")
                raise

    def unlock(self):
        if self.directory_id:
            try:
                fname = self.attachment_id.store_fname
                bucket = f"{google_bucket}"
                db_name = request.env['ir.config_parameter'].sudo().get_param('web.base.url').split("//")[1].split(".")[0]
                company_name = self.env.user.company_id.name
                file_path = f"{db_name}/{fname}"

                groups = self.directory_id.complete_group_ids.ids
                self.has_permission(groups_ids=groups, permission='perm_lock')

                # Download the encrypted file from Google Bucket
                encrypted_file_path = self._download_from_google_bucket(bucket, file_path, fname)

                # Log the full file path
                _logger.info(f"encrypted_file_path: {encrypted_file_path}")

                # Decrypt the file
                decrypted_content = self.decrypt_content(encrypted_file_path)

                # Ensure decryption success
                if not decrypted_content:
                    raise Exception("Decryption failed")

                # Confirm upload success
                if not self._check_upload_success(bucket, f"{db_name}/{fname}"):
                    raise Exception("Failed to upload decrypted file to Google Bucket")

                # Update the `datas` field with the base64-encoded decrypted file
                # with open(decrypted_content, 'rb') as file:
                #     decrypted_file_data = file.read()
                #     base64_decrypted_content = base64.b64encode(decrypted_file_data).decode('utf-8')

                # self.attachment_id.datas = base64_decrypted_content
                # self.attachment_id.mimetype = 'application/octet-stream'  # Set the correct MIME type if necessary
                
                # Replace the timestamp in the file path for the decrypted file
                # Get the first 9 digits of the current timestamp
                current_time_seconds = fname.split('-')[-1]
                new_timestamp = str(current_time_seconds)[:9]
                destination_blob_name = f"{db_name}/{fname}"
                updated_blob_name = re.sub(r'-\d+$', f'-{new_timestamp}', destination_blob_name)
                _logger.info(f"Updated destination_blob_name for decrypted file: {updated_blob_name}")

                # Upload the decrypted file back to Google Bucket
                self._upload_to_google_bucket(bucket, decrypted_content, updated_blob_name)

                # Get the folder path after 'temp-folder'
                folder_to_delete = os.path.dirname(encrypted_file_path)

                # Log the folder path to be deleted
                _logger.info(f"Folder to delete: {folder_to_delete}")

                # # Delete the folder after 'temp-folder'
                # if os.path.exists(folder_to_delete):
                #     shutil.rmtree(folder_to_delete)  # This deletes the folder and its contents
                #     _logger.info(f"Deleted folder: {folder_to_delete}")
                # else:
                #     _logger.error(f"Folder not found: {folder_to_delete}")

                # # Delete the encrypted file from Google Bucket
                # self._delete_from_google_bucket(bucket, updated_blob_name)

                self.write({"locked_by": None, 'is_locked': False})
                self.unlocked_by_owner()

                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            except Exception as e:
                _logger.error(f"Error during unlock: {e}")
                raise


    
    # ----------------------------------------------------------
    # Read, View
    # ----------------------------------------------------------
    def download_attachment(self):
        """
        Method to download the attachment.
        """
        self.ensure_one()
        groups = self.directory_id.complete_group_ids.ids
        self.has_permission(groups_ids=groups, permission='perm_download')
        attachment_field = self.attachment_ids
        if attachment_field:
            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content/%s?download=true' % (attachment_field[0].id),
                'target': 'current',
            }
        
    @api.depends("locked_by")
    def _compute_locked(self):
        for record in self:
            if record.locked_by.exists():
                record.update(
                    {
                        "is_locked": True,
                        "is_lock_editor": record.locked_by.id == record.env.uid,
                    }
                )
            else:
                record.update({"is_locked": False, "is_lock_editor": False})

     

    @api.depends('is_template')
    def _compute_directories_ids(self):
        for record in self:
            if record.is_template:
                record.directories_ids = record.env['dms.directory'].search([('is_deleted','=',False),('is_template','=',True)]).ids
            else:
                record.directories_ids = record.env['dms.directory'].search([('is_deleted','=',False),('is_template','=',False)]).ids
    

    def sanitize_url(self, url):
        return url.replace(" ", "%20")
    

    def unlink(self):
        for record in self:
            _logger.info('Unlink Document Id ........... %s',record.id)
            
            record.env['dms.json.version'].sudo().search([('document_id', '=', record.id)]).unlink()
            comments = record.env['document.comments'].sudo().search([('document_id', '=', record.id)])
            replies = record.env['document.reply'].sudo().search([('comment_id', 'in', comments.mapped('id'))])
            replies.unlink()
            comments.unlink()

            record.env['document.images'].sudo().search([('document_id', '=', record.id)]).unlink()
            record.env['document.load.image'].sudo().search([('doc_image_id', '=', record.id)]).unlink()
            record.env['document.sign'].sudo().search([('document_id', '=', record.id)]).unlink()
            record.env['share.by.qr'].sudo().search([('document_id', '=', record.id)]).unlink()

            record.delete_file_from_elastic_search(self.env.user.company_id.name, record.id)
            record.document_versions_ids.unlink()
        res = super(File,self).unlink()
        return res


    def locked_by_owner(self):
        for rec in self:
            rec.owner_lock = True
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
    def unlocked_by_owner(self):
        for rec in self:
            rec.owner_lock = False
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }

    def create_elastic_index(self, company_name, file_id, file_name, content):
        elastic_url = f"https://elastic.filesdna.com/index-file"
        headers = {
                        'Authorization': f'ApiKey UHJOWmU0c0JjM09ieEtGdDlVX2k6RGFQWko1NGtUemlmZmNKMFdBYkl3Zw==',
                        "Content-Type":"application/json",
                        
                        }
        elastic_payload = json.dumps({
                    "company_name": company_name,
                    "document_id": file_id,
                    "file_name": file_name,
                    "file_content": content
                    })
        response = requests.request("POST", elastic_url, headers=headers, data=elastic_payload)


    def delete_file_from_elastic_search(self, company_name, document_id):
        company_name = company_name.lower()
        company_name = re.sub(r'[^\w\s]', '_', company_name)  # Replace special characters with underscores
        company_name = re.sub(r'\s+', '_', company_name)      # Replace one or more spaces with a single underscore
        # ElasticSearch delete URL
        elastic_delete_url = f"https://elastic.filesdna.com:9200/{company_name}/_doc/{document_id}"
        headers = {
            'Authorization': 'ApiKey UHJOWmU0c0JjM09ieEtGdDlVX2k6RGFQWko1NGtUemlmZmNKMFdBYkl3Zw=='
        }

        try:
            # Make the DELETE request
            response = requests.delete(elastic_delete_url, headers=headers)

            # Check for successful response
            if response.status_code == 200:
                _logger.info(f"Successfully deleted document {document_id} for company {company_name} from ElasticSearch")
            else:
                _logger.error(f"Failed to delete document {document_id}. Status code: {response.status_code}, Response: {response.text}")
        
        except requests.RequestException as e:
            _logger.error(f"Error during ElasticSearch delete request: {e}")