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
from odoo.exceptions import ValidationError, UserError
from odoo.osv import expression
from odoo.tools import consteq, human_size
from odoo.tools.mimetypes import guess_mimetype
import hashlib
import mimetypes
from cryptography.fernet import Fernet
from odoo.http import request
from google.cloud import storage
from google.oauth2 import service_account
from ..tools import file
import os
from odoo.tools import config
import shutil
import re
from datetime import date, datetime
from markupsafe import Markup
from datetime import timedelta

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
        index=True)

    file_content = fields.Html('File Content', search=True)  # This field will use CKEditor 4
    directories_ids = fields.Many2many('dms.directory', string='Directory Filter', compute='_compute_directories_ids')
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
    # models/dms_file.py

    tag_ids = fields.Many2many(
        comodel_name="dms.tag",
        relation="dms_file_tag_rel",
        column1="fid",
        column2="tid",
        string="Tags Files",  # Not shown in views
        domain=[('type', '=', 'files')]
    )

    manual_tag_ids = fields.Many2many(
        comodel_name="dms.tag",
        compute="_compute_manual_tags",
        string="Tags",
        store=False
    )

    @api.depends('tag_ids')
    def _compute_manual_tags(self):
        for record in self:
            record.manual_tag_ids = record.tag_ids.filtered(lambda t: not t.auto_added)

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
                                                                   ], default='Draft', readonly=True)
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
    summary = fields.Html('Summary')
    notes = fields.Text('Notes')
    linked_fiels_ids = fields.One2many(comodel_name='dms.file.line', inverse_name='parent_file_id',
                                       string='Linked Files')
    linked_fiels = fields.Integer(compute='compute_linked_fiels', store=True, default=0, readonly=True,
                                  string='Linked Files')
    parent_id = fields.Many2one('dms.file', string="Parent File", ondelete='cascade')
    # child_ids = fields.One2many('dms.file', 'parent_id', string="Child Files")
    is_directory = fields.Boolean(string="Is Directory", default=False)
    # SHA-512 Hash
    sha512_hash = fields.Char(string='SHA-512 Hash', readonly=True)
    current_version_id = fields.Many2one('document.version', string='Current Version')
    document_versions_ids = fields.One2many(comodel_name='document.version', inverse_name='document_id',
                                            string='Document Versions')
    encription_user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    encription_key = fields.Char(string='Encription Key', related='encription_user_id.encription_key', readonly=True,
                                 store=True)

    # ---------------------- added fields -----------------------------------------
    is_template = fields.Boolean(string="Is template", default=False)
    is_uploaded = fields.Boolean(string="Is uploaded?", default=False)
    document_model = fields.Selection([
        ('normal', 'Normal'),
        ('crm', 'CRM'),
        ('itrack', 'iTrack'),
        ('matter', 'Matter'),
    ], default='normal')

    owner_lock = fields.Boolean(
        string="Locked By Owner",
        default=False,
        track_visibility='onchange'
    )
    # ----------inherit----------------------------------------
    doc_directory_number = fields.Char(string="Document Directory Number", related='directory_id.directory_number')
    # ----------------------------------------------------------
    # Amr's section
    # ----------------------------------------------------------
    is_pdf = fields.Boolean(string="Is PDF", compute="_compute_is_pdf", store=False)

    @api.depends('file_extension_id')
    def _compute_is_pdf(self):
        for record in self:
            record.is_pdf = (
                    record.file_extension_id and
                    record.file_extension_id.name and
                    record.file_extension_id.name.lower() == "pdf"
            )

    is_encrypted = fields.Boolean(string="Encrypted", default=False)
    security_status = fields.Html(
        string="Security Status",
        compute="_compute_security_status",
        store=True
    )

    @api.depends("owner_lock", "is_locked")
    def _compute_security_status(self):
        for record in self:
            status_icons = []

            if record.owner_lock:
                status_icons.append("🔒")  # Lock emoji
            if record.is_locked:
                status_icons.append("🛡️")  # Shield emoji (for encryption)

            record.security_status = " ".join(status_icons) if status_icons else "-"

            # 🔥 This makes the HTML safe to render
            record.security_status = Markup(" ".join(status_icons)) if status_icons else "-"

    active_security = fields.Boolean(string="Security Enabled", default=False)
    dms_security_id = fields.Many2one('dms.security', string="Security Option")

    file_name = fields.Char(string="File Name", compute="_compute_file_name", store=True)

    @api.depends('attachment_ids')
    def _compute_file_name(self):
        for record in self:
            if record.attachment_ids:
                record.file_name = record.attachment_ids[0].name
            else:
                record.file_name = "No File"

    # file_type = fields.Char(string="File Type", compute="_compute_file_type", store=True)

    @api.depends('attachment_ids')
    def _compute_file_type(self):
        """Computes the file type based on the file's mimetype or extension."""
        for record in self:
            if record.attachment_ids:
                attachment = record.attachment_ids[0]  # Get the first attachment
                mimetype = mimetypes.guess_extension(attachment.mimetype)
                if mimetype:
                    record.file_type = mimetype.upper().replace('.', '')  # Convert ".pdf" to "PDF"
                else:
                    filename, extension = os.path.splitext(attachment.name)
                    record.file_type = extension.upper().replace('.', '') if extension else "UNKNOWN"
            else:
                record.file_type = "UNKNOWN"

    def unlock_file(self):
        print('unlock')

    employee_id = fields.Many2one("hr.employee", string="Related Employee")

    file_extension_id = fields.Many2one(
        "dms.file.extension",
        string="File Extension",
        ondelete="set null",
    )

    file_extension_image = fields.Image(
        related="file_extension_id.file_image",
        string="File Type",
        readonly=True,
        max_width=32,
        max_height=32
    )

    disable_directory = fields.Boolean(
        string="Disable Directory Selection",
        compute="_compute_disable_directory",
        store=False
    )

    @api.depends("create_uid")  # Using a hashable field to trigger computation
    def _compute_disable_directory(self):
        """ Compute the disable_directory based on system settings """
        config_param = self.env["ir.config_parameter"].sudo()
        enable_template_creation = config_param.get_param("dms.enable_directory_creation", "False") == "True"
        for record in self:
            record.disable_directory = enable_template_creation

    # ----------------------------------------------------------
    # End of amr's section
    # ----------------------------------------------------------

    is_late = fields.Boolean()

    def check_date_file(self):
        print('check_date_file')
        # Get all dms.file records
        all_files = self.env['dms.file'].search([])

        for dms_file in all_files:
            # Get all dms.line records associated with the current dms.file
            dms_lines = dms_file.line_ids

            for line in dms_lines:
                if line.request_date and line.request_date < fields.Datetime.now() - timedelta(days=5):
                    print('request_date=', line.request_date)
                    print('date today =', fields.Datetime.now())
                    print('diff =', line.request_date < fields.Datetime.now() - timedelta(days=5))
                    dms_file.is_late = True
                    dms_file.state = 'delayed'
                    break
                else:
                    dms_file.is_late = False

    create_date = fields.Date(
        string='Create Date',
        default=fields.Date.context_today)

    document_date = fields.Date(
        string='Document Date')
    document_number = fields.Char()

    @api.model
    def _get_default_reference(self):
        # Choose the logic you want here (e.g., first record, one with a flag, etc.)
        return self.env['dms.reference'].search([], limit=1).id

    reference = fields.Char(default='New', readonly=1)
    reference_id = fields.Many2one('dms.reference', required=True, default=lambda self: self._get_default_reference())
    reference_name = fields.Char(related='reference_id.reference_name')
    reference_name_start = fields.Integer(related='reference_id.start')
    reference_name_without_start = fields.Char(related='reference_id.reference_name_without_start')
    total = fields.Integer(compute='_compute_total', index=True, store=True)
    doc_number = fields.Char(string='Document Number')

    @api.depends('reference_id')
    def _compute_total(self):
        for rec in self:
            rec.total = rec.reference_name_start + int(rec.doc_number)

    notes = fields.Text(
        string='Notes'
    )

    important_notes = fields.Text(
        string='Important Notes'
    )

    selected_users = fields.One2many(
        'dms.file.user.selection',
        'file_id',
        string='Selected Users'
    )

    change_log_ids = fields.One2many(
        'dms.file.change.log',
        'file_id',
        string='Change Logs'
    )
    # itrack_id = fields.Many2one(comodel_name='itrack.document.eat', string='iTrack')
    # line_ids = fields.One2many('dms.line', 'file_id')
    dms_line_id = fields.Many2one('dms.line')
    # copy_line_ids = fields.One2many('copy.to', 'copy_to_id')
    parent_root_dms = fields.Many2one('hr.department', domain="[('parent_id', '=', False)]",
                                      compute='_compute_parent_root')
    # doc_parm_file = fields.One2many('document.parameters.line.file', 'dms_file')
    # -----------------------------------------------------------------------------
    # Dynamic fields for document parameters
    parameter_values = fields.One2many('dms.link.document.parameter.line', 'file_id', string="Document Parameters",
                                       store=True, index=True)
    perm_access = fields.Many2many('document.parameters.line', compute='_compute_perm_access', store=False, index=True)
    perm_domain = fields.Char(store=True, index=True)

    enable_document_filter = fields.Boolean(
        string='Enable Document Filter',
        store=True,

    )

    @api.onchange('enable_document_filter')
    def _compute_enable_document_filter(self):
        config = self.env['ir.config_parameter'].sudo()
        self.enable_document_filter = config.get_param("dms.enable_document_filter", "False") == "True"

    @api.depends('access_id.parameter_values_access')
    def _compute_perm_access(self):
        for record in self:
            all_selected_value_ids = []
            selected_value_to_parameter = {}
            perms = record.access_id.parameter_values_access
            for perm in perms:
                for selected_value in perm.selected_value_ids:
                    all_selected_value_ids.append(selected_value.id)
                    parameter_id = selected_value.document_parameters.id
                    selected_value_to_parameter[selected_value.id] = parameter_id
            all_selected_value_ids = sorted(set(all_selected_value_ids))
            record.perm_access = [(6, 0, all_selected_value_ids)]
            grouped_output = {}
            for selected_value_id, parameter_id in selected_value_to_parameter.items():
                if parameter_id not in grouped_output:
                    grouped_output[parameter_id] = []
                grouped_output[parameter_id].append(selected_value_id)
            formatted_output = []
            for value_ids in grouped_output.values():
                formatted_output.append(f"[{','.join(map(str, value_ids))}]")
            output_string = " and ".join(formatted_output)
            record.perm_domain = output_string
            print('Formatted Output:', output_string)

    @api.model
    def default_get(self, fields_list):
        """ Auto-populate parameters when creating a new document """
        res = super(File, self).default_get(fields_list)
        parameters = self.env['document.parameters'].search([])
        parameters_lines = self.env['document.parameters.line'].search([])
        print('parameters=', parameters)
        print('parameters_lines=', parameters_lines)
        parameter_values = []
        for param in parameters:
            # Find the first selected value for the current parameter
            first_selected_value_id = parameters_lines.filtered(lambda line: line.document_parameters == param).ids
            if first_selected_value_id:
                selected_value_id = first_selected_value_id[0]
            else:
                selected_value_id = False
            parameter_values.append((0, 0, {
                'parameter_id': param.id,
                'selected_value_id': selected_value_id,
            }))
        res['parameter_values'] = parameter_values
        print('res=', res)
        return res

    perm_create = fields.Boolean(related='directory_id.group_ids.perm_create', store=True)
    perm_unlink = fields.Boolean(related='directory_id.group_ids.perm_unlink', store=True)
    perm_write = fields.Boolean(related='directory_id.group_ids.perm_write', store=True)

    def _compute_parent_root(self):
        user = self.env.user
        ministry_id = user.employee_id.ministry_id if user.employee_id else False
        for rec in self:
            if ministry_id:
                rec.parent_root_dms = ministry_id.id
            else:
                rec.parent_root_dms = False
            print('root=', ministry_id.name if ministry_id else 'No ministry assigned')
            # access = self.env.user.access_id
            # print('access=', access)
            # if access:
            #     rec.perm_open_locally = access.perm_open_locally
            #     rec.perm_edit_online = user.access_id.perm_edit_online
            #     rec.perm_preview_file = user.access_id.perm_preview_file
            #     rec.perm_download = user.access_id.perm_download

            # Handle multiple groups
            if rec.directory_id.group_ids:
                for group in rec.directory_id.group_ids:
                    if group.perm_create and group.perm_unlink:
                        print('create file=', group.perm_create)
                        print('delete file=', group.perm_unlink)
                    if group.perm_create and not group.perm_unlink:
                        print('create file=', group.perm_create)
                        print('delete file=', group.perm_unlink)
                    if not group.perm_create and group.perm_unlink:
                        print('create file=', group.perm_create)
                        print('delete file=', group.perm_unlink)
                        raise ValidationError("You Don't Have Access To Create This File")
                    if not group.perm_create and not group.perm_unlink:
                        print('create file=', group.perm_create)
                        print('delete file=', group.perm_unlink)
                        raise ValidationError("You Don't Have Access To Create And Delete This File")

    def action_send_invite(self):
        """Send activity to users who haven't been invited."""
        for record in self:
            users_to_invite = record.selected_users.filtered(lambda u: not u.is_invited)
            if not users_to_invite:
                raise UserError("All selected users have already been invited.")
            for user_selection in users_to_invite:
                user = user_selection.user_id
                self.env['mail.activity'].create({
                    'res_id': record.id,
                    'res_model_id': self.env['ir.model']._get('dms.file').id,
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'summary': f'Please review the file: {record.name}',
                    'user_id': user.id,
                    'note': f"You are invited to review the document '{record.name}'",
                })
                user_selection.is_invited = True

    # -------------------Box File----------------------------------
    reference_box_file = fields.Char(default='New', readonly=1)
    file = fields.Char()
    person_concerned = fields.Char()
    note = fields.Char()
    file_number = fields.Integer()

    itrack_count = fields.Integer(
        string='iTrack', compute='_compute_itrack'
    )

    def _compute_itrack(self):
        for record in self:
            record.itrack_count = self.env['itrack.document.eat'].search_count([
                ('dms_line_ids', 'in', record.ids)
            ])

    def action_view_itrack(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'iTrack Request',
            'res_model': 'itrack.document.eat',
            'view_mode': 'tree,form',
            'domain': [('dms_line_ids', 'in', self.ids)],
            'context': dict(self.env.context, create=False),
        }

    def action_create_itrack_request(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'iTrack Link',
            # 'res_model': 'itrack.document.eat',
            'res_model': 'dms.itrack.link.wizard',
            'view_mode': 'form',
            'target': 'new'
        }

    def move_documents_to_archive(self):
        """Move documents to archive based on classification and creation date."""
        archive_directories = {
            'a': 'Archive 5',
            'b': 'Archive 10',
            'c': 'Archive 15'
        }
        years_to_add = {
            'a': 5,
            'b': 10,
            'c': 15
        }

        today = fields.Date.context_today(self)

        for classification, years in years_to_add.items():
            # Calculate the archive deadline
            archive_deadline = fields.Date.to_date(today) - timedelta(days=years * 365)
            print(archive_deadline)
            # Fetch target directory for this classification
            target_directory = self.env['dms.directory'].search([
                ('name', '=', archive_directories[classification])
            ], limit=1)

            if target_directory:
                # Update the directory for all matching records in one batch operation
                files = self.env['dms.file'].search([
                    ('classification', '=', classification),
                    ('create_date', '<=', archive_deadline),
                    ('directory_id.is_archive_dir', '=', False)
                ])
                print(files, target_directory.name)
                files.sudo().write({'directory_id': target_directory.id})

    itrack_count = fields.Integer(
        string='ITrack', compute='_compute_count_itrack'
    )

    def _compute_count_itrack(self):
        for record in self:
            print('_compute_count_itrack')
            record.itrack_count = self.env['dms.line'].search_count([
                ('file_id', '=', record.id)
            ])
            print('extension=', record.extension)

            # Search for the record
            search_extension = self.env['dms.file.extension'].search([('name', '=', record.extension)], limit=1)
            if search_extension:
                print('search_extension=', search_extension.name)
                if record.extension == search_extension.name:
                    print('testing=', record.extension, search_extension.name)
                    print('id for values=', record.parameter_values.selected_value_id)
                    record.file_extension_id = search_extension.id
            else:
                search_extension_noname = self.env['dms.file.extension'].search([('name', '=', 'no_name')], limit=1)
                print('search_extension_noname=', search_extension_noname)
                record.file_extension_id = search_extension_noname.id

    def set_extension(self):
        for record in self:
            print('extension=', record.extension)
            # Search for the record
            search_extension = self.env['dms.file.extension'].search([('name', '=', record.extension)], limit=1)
            if search_extension:
                print('search_extension=', search_extension.name)
                if record.extension == search_extension.name:
                    print('testing=', record.extension, search_extension.name)
                    print('id for values=', record.parameter_values.selected_value_id)
                    record.file_extension_id = search_extension.id
            else:
                search_extension_noname = self.env['dms.file.extension'].search([('name', '=', 'no_name')], limit=1)
                print('search_extension_noname=', search_extension_noname)
                record.file_extension_id = search_extension_noname.id

    def action_view_itrack(self):
        print('action_view_itrack')
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'ITrack',
            'res_model': 'dms.line',
            'view_mode': 'tree,form',
            'domain': [('file_id', '=', self.id)],
            'context': dict(self.env.context, create=True, default_file_id=self.id),
        }

    change_log_count = fields.Integer(
        string='Change Log', compute='_compute_change_log'
    )

    def _compute_change_log(self):
        for record in self:
            record.change_log_count = self.env['dms.file.change.log'].search_count([
                ('file_id', '=', record.id)
            ])

    def action_view_change_log(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Change log',
            'res_model': 'dms.file.change.log',
            'view_mode': 'tree,form',
            'domain': [('file_id', '=', self.id)],
            'context': dict(self.env.context, create=False),
        }

    # ----------------------------------------------------------
    access_id = fields.Many2one('dms.access.group')
    # access_doc_params_line_ids = fields.One2many(related='access_id.document_ids.document_parameters_line')

    access_archive = fields.Many2one('dms.access.group', string='Archive',
                                     domain="[('name', 'in', ['Archive group 5', 'Archive group 10', 'Archive group 15'])]")
    access_name = fields.Char(compute='_compute_name_group')
    perm_lock = fields.Boolean(related='access_id.perm_lock', store=True)
    perm_unlock = fields.Boolean(related='access_id.perm_unlock', store=True)
    perm_download = fields.Boolean(related='directory_id.group_ids.perm_download', store=True)
    perm_encrypt = fields.Boolean(related='directory_id.group_ids.perm_encrypt', store=True)
    perm_open_locally = fields.Boolean(related='directory_id.group_ids.perm_open_locally', store=True)
    perm_edit_online = fields.Boolean(related='directory_id.group_ids.perm_edit_online', store=True)
    perm_preview_file = fields.Boolean(related='directory_id.group_ids.perm_preview_file', store=True)

    # # @api.onchange('access_id')
    # def _compute_access_id_perm(self):
    #     print('user=', self.env.user.name)
    #     user = self.env.user.access_id
    #     for rec in self:
    #         if user:
    #             print('user access=', user.perm_open_locally)
    #             rec.perm_open_locally = user.perm_open_locally
    #             print('perm_open_locally=', self.perm_open_locally)

    def _compute_name_group(self):
        for rec in self:
            rec.access_name = rec.access_id.id

    def action_open_link_file_selector_wizard(self):
        """Open the wizard to link multiple files."""
        self.ensure_one()
        return {
            'name': 'Link Files',
            'type': 'ir.actions.act_window',
            'res_model': 'dms.link.files.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_parent_file_id': self.id},
        }

    def action_link_files(self):
        print('action_link_files')

        for record in self:
            existing_record = self.env['dms.file.line'].search([('file_id', '=', record.id)], limit=1)

            if not existing_record:
                link_record = self.env['dms.file.line'].create({
                    'file_id': record.id,
                })
                print('link_record=', link_record)
            else:
                print('هذا المعرف موجود بالفعل، لن يتم إنشاء سجل جديد.')

    @api.onchange('name')
    def onchange_name(self):
        if self.directory_id:
            groups = self.directory_id.complete_group_ids.ids
            self.has_permission(groups_ids=groups, permission='perm_rename')

    def write(self, vals):

        for record in self:
            for field, new_value in vals.items():
                old_value = record[field]
                field_info = self._fields[field]
                ttype = field_info.type

                if ttype == 'many2many' or ttype == 'one2many':
                    continue

                elif ttype == 'many2one' and old_value != new_value:
                    model_id = self.env['ir.model'].sudo().search([('model', '=', 'dms.file')]).id
                    field_object = self.env['ir.model.fields'].sudo().search(
                        [('name', '=', field), ('model_id', '=', model_id)])
                    record_name = self.env[f'{field_object.relation}'].sudo().search([('id', '=', new_value)]).name
                    self.env['dms.file.change.log'].sudo().create({
                        'file_id': record.id,
                        'field_name': field_object.field_description,
                        'old_value': getattr(old_value, 'name', old_value) if old_value else None,
                        'new_value': record_name,
                        'user_id': self.env.uid,
                    })

                elif ttype == 'selection':
                    model_id = self.env['ir.model'].sudo().search([('model', '=', 'dms.file')]).id
                    field_object = self.env['ir.model.fields'].sudo().search(
                        [('name', '=', field), ('model_id', '=', model_id)])
                    selection_recs = field_object.selection_ids.sudo().search_read([('field_id', '=', field_object.id)])
                    for sel in selection_recs:
                        if sel['value'] == old_value:
                            old_value = sel['display_name']
                        if sel['value'] == new_value:
                            new_value = sel['display_name']

                    self.env['dms.file.change.log'].sudo().create({
                        'file_id': record.id,
                        'field_name': field_object.field_description,
                        'old_value': old_value,
                        'new_value': new_value,
                        'user_id': self.env.uid,
                    })
                else:
                    model_id = self.env['ir.model'].sudo().search([('model', '=', 'dms.file')]).id
                    field_object = self.env['ir.model.fields'].sudo().search(
                        [('name', '=', field), ('model_id', '=', model_id)])
                    self.env['dms.file.change.log'].sudo().create({
                        'file_id': record.id,
                        'field_name': field_object.field_description,
                        'old_value': old_value,
                        'new_value': new_value,
                        'user_id': self.env.uid,
                    })
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
                    "res_id": document_version.id,
                }
            )
        )
        document_version.write({'attachment_id': attachment.id,
                                'attachment_ids': [(6, 0, attachment.ids)]})
        file_name = attachment.name
        fname = attachment.store_fname
        user = self.env['res.users'].search([('id', '=', self.env.user.id)])
        if user and self.extension == "pdf" and not self.is_uploaded:
            fname = attachment.store_fname
            current_time_seconds = time.time()
            current_time_milliseconds = int(current_time_seconds)
            self.current_time_seconds = current_time_milliseconds
        # //////////////////////////////// create elastic index /////////////////////////////////

    def _create_new_version(self, new_attachment_ids):
        if new_attachment_ids:
            for attachment_id in new_attachment_ids:
                if attachment_id:
                    attachment = attachment_id if isinstance(attachment_id, int) else attachment_id[-1] if isinstance(
                        attachment_id, list) else None
                    if attachment:
                        attachment_obj = self.env['ir.attachment'].search([('id', '=', attachment)], limit=1)
                        if attachment_obj:
                            attachment_ids = attachment_obj.ids if isinstance(attachment_obj.ids, list) else [
                                attachment_obj.ids]
                            self.attachment_ids = [(6, 0, attachment_ids)]
                            self.create_document_version(document_name=self.attachment_ids[0].name, document_id=self.id,
                                                         data=self.attachment_ids[0].datas)
                            self.save_encrypted_file(self.attachment_ids[0].datas,
                                                     '/opt/filesdna17/custom_addons/encrypted_image.enc')
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
                                                column2="decript_id", )
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
        groups_with_permission = self.env['dms.access.group'].search(
            [('id', 'in', groups_ids), (permission, '=', True)])
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
            # if permission == 'perm_write':
            #     raise ValidationError("You do not have permission to edit this record.")
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

    # # ----------------------------------------------------------
    # # SearchPanel
    # # ----------------------------------------------------------
    # #
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

    #
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
            # return {"parent_field": "parent_id", "values": list(field_range.values())}

        context = {}
        if field_name == "category_id":
            context["category_short_name"] = True
        return super(File, self.with_context(**context)).search_panel_select_range(
            field_name, **kwargs
        )

    # # ------- Zenab -------------
    @api.model
    def get_directory_for_panel(self, directory_id):
        directory = self.env['dms.directory'].sudo().search([('id', '=', int(directory_id))])
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
            company_image = record.env['res.company.dms'].search([('file_extension', '=', file_extension)],
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
        """Create an ir.attachment record and link it to a dms.file."""
        res_vals = vals.copy()

        # 🔍 Resolve directory ID (optional logic—can be removed if unused)
        directory_id = (
                res_vals.get("directory_id")
                or self.env.context.get("active_id")
                or self.env.context.get("default_directory_id")
        )

        if directory_id:
            self.env["dms.directory"].browse(directory_id)  # Validate (if needed, currently unused)

        attachment = self.env["ir.attachment"].create({
            "name": vals.get("name", "Unnamed File"),
            "datas": vals.get("content"),
            "res_model": "dms.file",
            "res_id": vals.get("id"),
        })

        res_vals["attachment_id"] = attachment.id
        return res_vals

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})

        # Get file names in target directory
        directory_id = default.get("directory_id", self.directory_id.id)
        directory = self.env["dms.directory"].browse(directory_id).sudo()
        existing_names = directory.file_ids.mapped("name")

        # Generate a unique name
        default["name"] = file.unique_name(self.name, existing_names, self.extension)
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
        for record in self:
            if record.active_security or record.is_locked or record.owner_lock:
                raise UserError(
                    _("You cannot delete this file because it is locked, encrypted, or has active security enabled.")
                )
            _logger.info('Unlink Document Id ........... %s', record.id)
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

    def compute_sha512_hash(self, file_path):
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
        credentials = service_account.Credentials.from_service_account_file(
            f"/opt/filesdna17/custom_addons/google_cloud_storage/google_creds.json")
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
        """Automatically create files and assign them to dynamically created directories based on user-selected template."""
        config = self.env["ir.config_parameter"].sudo()
        enable_directory_creation = config.get_param("dms.enable_directory_creation", "False") == "True"
        selected_template_id = config.get_param("dms.directory_template_id")
        selected_template = self.env["dms.directory.template"].browse(
            int(selected_template_id)) if selected_template_id else False
        user = self.env.user
        employee = user.employee_id
        # New check for document filter
        enable_document_filter = config.get_param("dms.enable_document_filter", "False") == "True"

        if employee and employee.unit_id:
            unit_name = employee.unit_id.name if hasattr(employee.unit_id, "name") else str(employee.unit_id)
        else:
            unit_name = None
        storage = self.env["dms.storage"].search([], limit=1)
        access_group = self.env["dms.access.group"].search([("users", "=", user.id)], limit=1)

        if enable_directory_creation and not unit_name:
            raise ValidationError("No valid unit name found for the employee.")

        if enable_directory_creation and not storage:
            raise ValidationError("No storage found! Please create a storage before proceeding.")

        new_vals_list = []

        for vals in vals_list:
            if enable_document_filter and not vals.get("parameter_values"):
                raise ValidationError("You need to create document parameters.")

            file_name = vals.get("name")
            file_content = vals.get("content")
            # parameter_values = vals.get("parameter_values", [])

            _logger.info(f"🔄 Processing file: {file_name}")

            # ✅ Validation
            if not file_content:
                raise ValidationError(f"File '{file_name}' has no content. Please re-upload.")

            # for pv in parameter_values:
            #     if pv[0] == 0 and not pv[2].get("selected_value_id"):
            #         raise ValidationError("Please select a value for all document parameters before saving.")

            # ✅ Hashing & Access Group
            vals["sha512_hash"] = self.generate_sha512(file_content)
            vals["access_id"] = access_group.id if access_group else None

            # ✅ Create Attachment
            attachment_vals = self._create_model_attachment(vals)
            if not attachment_vals.get("attachment_id"):
                raise ValidationError(f"Attachment creation failed for '{file_name}'")

            # ✅ Set doc_number
            if vals.get("reference_id"):
                last_doc = self.search([('reference_id', '=', vals['reference_id'])], order='doc_number desc', limit=1)
                vals["doc_number"] = int(last_doc.doc_number) + 1 if last_doc else 1

            # ✅ Append for creation
            new_vals_list.append(self._create_model_attachment(vals))

        # ✅ Bulk create
        created_records = super().create(new_vals_list)

        # ✅ Create Directories if enabled
        if enable_directory_creation:
            _logger.info(f"✅ Directory creation is ENABLED for unit: {unit_name}")
            template = selected_template if selected_template and selected_template.exists() else \
                self.env["dms.directory.template"].search([("name", "=", unit_name)], limit=1)

            # ✅ Create new template if not found
            if not template:
                template = self.env["dms.directory.template"].create({"name": unit_name})
                structure_data = [
                    {"name": unit_name, "is_root": True, "parent_id": None},
                    {"name": "in-docs", "parent_id": unit_name},
                    {"name": "out-docs", "parent_id": unit_name},
                    {"name": str(datetime.now().year), "parent_id": "in-docs"},
                    {"name": str(datetime.now().year), "parent_id": "out-docs"},
                ]
                created_templates = {}
                for item in structure_data:
                    parent_id = created_templates.get(item["parent_id"])
                    line = self.env["dms.directory.template.line"].create({
                        "name": item["name"],
                        "template_id": template.id,
                        "is_root": item.get("is_root", False),
                        "parent_id": parent_id,
                    })
                    created_templates[item["name"]] = line.id
                _logger.info(f"✅ Created directory template for {unit_name}")

            for record in created_records:
                in_out = record.parameter_values.selected_value_id.name
                structure = {
                    "root": {"name": unit_name, "parent_id": None, "is_root_directory": True},
                    "doc_folder": {"name": "in-docs" if in_out == "In" else "out-docs", "parent_id": "root"},
                    "year": {"name": str(datetime.now().year), "parent_id": "doc_folder"},
                }
                created_dirs = {}
                for key, val in structure.items():
                    parent_id = created_dirs.get(val["parent_id"])
                    domain = [("name", "=", val["name"])]
                    domain.append(("parent_id", "=", parent_id) if parent_id else ("is_root_directory", "=", True))
                    directory = self.env["dms.directory"].search(domain, limit=1)

                    if not directory:
                        if user.access_id_many:
                            # Get a list of access group IDs
                            group_ids = user.access_id_many.ids  # This gets a list of IDs directly
                            # Ensure group_ids is not empty and only has valid IDs
                            if group_ids:
                                directory = self.env["dms.directory"].create({
                                    "name": val["name"],
                                    "parent_id": parent_id,
                                    "template_id": template.id,
                                    "storage_id": 1,
                                    "is_root_directory": val.get("is_root_directory", False),
                                    "group_ids": [(6, 0, group_ids)]
                                })
                                created_dirs[key] = directory.id
                                print('directory=', directory.name)
                            else:
                                _logger.warning("No valid access group IDs found.")
                        else:
                            _logger.warning("No access groups found.")
                    else:
                        # If the directory already exists, store its ID
                        created_dirs[key] = directory.id

                if not created_dirs.get("year"):
                    raise ValidationError(
                        "Could not assign a valid directory. Ensure the template is correctly structured.")
                record.write({"directory_id": created_dirs["year"]})
        else:
            _logger.info("🚫 Directory creation is DISABLED. Skipping structure.")
        # ✅ Auto Tagging
        if config.get_param("dms.enable_auto_tagging", "False") == "True":
            email_prefix = user.login.split("@")[0]
            email_tag = self.env["dms.tag"].search([("name", "=", email_prefix)], limit=1) or \
                        self.env["dms.tag"].create({"name": email_prefix, "auto_added": True, "type": 'files'})

            group_tags = []
            for group in self.env["dms.access.group"].search([("users", "in", user.id)]):
                tag = self.env["dms.tag"].search([("name", "=", group.name)], limit=1)
                if not tag:
                    tag = self.env["dms.tag"].create({"name": group.name, "auto_added": True, "type": 'files'})
                group_tags.append(tag.id)

            for record in created_records:
                tag_ids = [email_tag.id] + group_tags
                record.write({'tag_ids': [(4, tag_id) for tag_id in tag_ids]})

        # ✅ Link attachments + Generate references
        sequence = self.env["ir.sequence"]
        for record in created_records:
            if record.attachment_id:
                record.attachment_id.res_id = record.id
                record.attachment_ids = record.attachment_id.ids
                _logger.info(f"🔗 Linked attachment {record.attachment_id.id} to file {record.id}")

            if record.reference == "New":
                record.reference = f"{record.reference_name_without_start}{record.total}"
            if record.reference_box_file == "New":
                record.reference_box_file = sequence.next_by_code("box_file_sequence") or "/"

        # ✅ Locking (if enabled for user)
        if user.is_auto_lock:
            for record in created_records:
                record.lock()

        _logger.info(f"✅ Completed creation of {len(created_records)} files")

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
                'name': _('Files'),
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
        for record in self:
            if record.active_security or record.is_locked or record.owner_lock:
                raise UserError(
                    _("You cannot delete this file because it is locked, encrypted, or has active security enabled.")
                )
            _logger.info('Unlink Document Id ........... %s', record.id)
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
                    'name': _('Files'),
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
        if not self.directory_id:
            return

        try:
            fname = self.attachment_id.store_fname
            company_name = self.env.user.company_id.name
            db_name = self._cr.dbname
            file_path = f"{db_name}/{fname}"
            bucket = google_bucket

            _logger.info(f"🔒 Starting lock process for: {file_path}")

            # Check permissions
            self.has_permission(groups_ids=self.directory_id.complete_group_ids.ids, permission='perm_lock')

            # Download file
            local_file_path = self._download_from_google_bucket(bucket, file_path, fname)
            _logger.info(f"✅ File downloaded locally: {local_file_path}")

            # Encrypt
            encrypted_content = self._encrypt_content(local_file_path, is_unlocked=False)
            if not encrypted_content:
                raise Exception("Encryption failed")

            _logger.info(f"✅ File encrypted: {encrypted_content}")

            # Upload encrypted version
            self._upload_to_google_bucket(bucket, encrypted_content, file_path)
            _logger.info(f"✅ Encrypted file uploaded to: {file_path}")

            if not self._check_upload_success(bucket, file_path):
                raise Exception("Upload verification failed")

            # Update record
            self.write({"locked_by": self.env.uid, 'is_locked': True})
            self.locked_by_owner()

            return {'type': 'ir.actions.client', 'tag': 'reload'}

        except Exception as e:
            _logger.error(f"❌ Lock error for file {fname}: {e}")
            raise

    def unlock(self):
        if not self.directory_id:
            return

        try:
            fname = self.attachment_id.store_fname
            db_name = self._cr.dbname
            file_path = f"{db_name}/{fname}"
            bucket = google_bucket

            _logger.info(f"🔓 Starting unlock process for: {file_path}")

            # Check permissions
            self.has_permission(groups_ids=self.directory_id.complete_group_ids.ids, permission='perm_lock')

            # Download encrypted file
            encrypted_file_path = self._download_from_google_bucket(bucket, file_path, fname)
            _logger.info(f"✅ Encrypted file downloaded: {encrypted_file_path}")

            # Decrypt
            decrypted_content = self.decrypt_content(encrypted_file_path)
            if not decrypted_content:
                raise Exception("Decryption failed")

            # Generate updated blob name
            timestamp = fname.split('-')[-1]
            new_timestamp = str(timestamp)[:9]
            updated_blob_name = re.sub(r'-\d+$', f'-{new_timestamp}', file_path)
            _logger.info(f"📝 Updated blob path: {updated_blob_name}")

            # Upload decrypted version
            self._upload_to_google_bucket(bucket, decrypted_content, updated_blob_name)

            if not self._check_upload_success(bucket, updated_blob_name):
                raise Exception("Upload verification failed")

            # Clean up temp local folder
            folder_to_delete = os.path.dirname(encrypted_file_path)
            _logger.info(f"🧹 Folder scheduled for deletion: {folder_to_delete}")
            # Uncomment when safe
            # shutil.rmtree(folder_to_delete)

            # Optionally delete from bucket
            # self._delete_from_google_bucket(bucket, updated_blob_name)

            # Update record
            self.write({"locked_by": None, 'is_locked': False})
            self.unlocked_by_owner()

            return {'type': 'ir.actions.client', 'tag': 'reload'}

        except Exception as e:
            _logger.error(f"❌ Unlock error for file {fname}: {e}")
            raise

    def action_preview(self):
        print('action preivew')

    def action_open_locally(self):
        print('action_open_locally')

    def action_edit(self):
        for record in self:
            # Ensure the record is valid
            record.ensure_one()
            # Define the online editor URL
            base_url = '/react/home'
            query_params = f"?data_path={record.sha512_hash}-{record.current_time_seconds}"
            # Return an action to open the editor
            _logger.info(f"Editing file online with URL: {base_url + query_params}")
            return {
                'type': 'ir.actions.act_url',
                'url': base_url + query_params,
                'target': 'self',
            }

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
                _logger.info(f"########## is locked: {record.is_locked}")
            else:
                record.update({"is_locked": False, "is_lock_editor": False})

    @api.depends('is_template')
    def _compute_directories_ids(self):
        for record in self:
            if record.is_template:
                record.directories_ids = record.env['dms.directory'].search(
                    [('is_deleted', '=', False), ('is_template', '=', True), ('is_archive_dir', '=', False)]).ids
            else:
                record.directories_ids = record.env['dms.directory'].search(
                    [('is_deleted', '=', False), ('is_template', '=', False), ('is_archive_dir', '=', False)]).ids

    def sanitize_url(self, url):
        return url.replace(" ", "%20")

    def unlink(self):
        for record in self:
            if not record.perm_unlink:
                raise UserError(_(
                    "You Dont Have Permissions To Delete This File"
                ))

            # ✅ Prevent deletion of protected files
            if record.active_security or record.is_locked or record.owner_lock:
                raise UserError(_(
                    "You cannot delete this file because it is locked, encrypted, or has active security enabled."
                ))

            _logger.info("🗑️ Unlinking Document ID: %s", record.id)

            # ✅ Predefine env models
            JsonVersion = self.env['dms.json.version'].sudo()
            Comments = self.env['document.comments'].sudo()
            Replies = self.env['document.reply'].sudo()
            Images = self.env['document.images'].sudo()
            LoadImages = self.env['document.load.image'].sudo()
            Signs = self.env['document.sign'].sudo()
            QRShare = self.env['share.by.qr'].sudo()

            # ✅ Cascade delete related records
            JsonVersion.search([('document_id', '=', record.id)]).unlink()

            # Delete comments and their replies
            comments = Comments.search([('document_id', '=', record.id)])
            if comments:
                Replies.search([('comment_id', 'in', comments.ids)]).unlink()
                comments.unlink()

            # Delete images and other linked models
            Images.search([('document_id', '=', record.id)]).unlink()
            LoadImages.search([('doc_image_id', '=', record.id)]).unlink()
            Signs.search([('document_id', '=', record.id)]).unlink()
            QRShare.search([('document_id', '=', record.id)]).unlink()

            # ✅ Remove document versions
            record.document_versions_ids.unlink()

            # ✅ If needed: remove from external systems like ElasticSearch
            # record.delete_file_from_elastic_search(self.env.user.company_id.name, record.id)

        return super(File, self).unlink()

    def locked_by_owner(self):
        for rec in self:
            rec.owner_lock = True
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def unlocked_by_owner(self):
        for rec in self:
            rec.owner_lock = False
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def create_elastic_index(self, company_name, file_id, file_name, content):
        url = "https://elastic.filesdna.com/index-file"
        headers = {
            'Authorization': 'ApiKey UHJOWmU0c0JjM09ieEtGdDlVX2k6RGFQWko1NGtUemlmZmNKMFdBYkl3Zw==',
            'Content-Type': 'application/json',
        }
        payload = json.dumps({
            "company_name": company_name,
            "document_id": file_id,
            "file_name": file_name,
            "file_content": content
        })

        try:
            response = requests.post(url, headers=headers, data=payload)
            if response.status_code == 200:
                _logger.info(f"📥 Indexed document {file_id} successfully into ElasticSearch.")
            else:
                _logger.warning(
                    f"⚠️ ElasticSearch index failed. Status {response.status_code}, Response: {response.text}")
        except requests.RequestException as e:
            _logger.error(f"❌ Error indexing file to ElasticSearch: {e}")

    def delete_file_from_elastic_search(self, company_name, document_id):
        clean_company = re.sub(r'[^\w\s]', '_', company_name.lower())
        clean_company = re.sub(r'\s+', '_', clean_company)

        url = f"https://elastic.filesdna.com:9200/{clean_company}/_doc/{document_id}"
        headers = {
            'Authorization': 'ApiKey UHJOWmU0c0JjM09ieEtGdDlVX2k6RGFQWko1NGtUemlmZmNKMFdBYkl3Zw=='
        }

        try:
            response = requests.delete(url, headers=headers)
            if response.status_code == 200:
                _logger.info(
                    f"🗑️ Successfully deleted document {document_id} for company '{clean_company}' from ElasticSearch")
            else:
                _logger.error(
                    f"❌ Failed to delete document {document_id}. Status {response.status_code}, Response: {response.text}")
        except requests.RequestException as e:
            _logger.error(f"❌ ElasticSearch delete request failed: {e}")

    def action_open_file(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('DMS File'),
            'res_model': 'dms.file',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    @api.model
    def get_log_notes_data(self, record_id):
        record = self.browse(record_id)
        if not record.exists():
            return []

        messages = self.env['mail.message'].search([
            ('model', '=', 'dms.file'),
            ('res_id', '=', record.id)
        ])

        return [{
            'author': msg.author_id.name,
            'body': msg.body,
            'date': msg.date,
        } for msg in messages]
