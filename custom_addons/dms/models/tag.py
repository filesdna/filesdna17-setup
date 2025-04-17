import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class Tag(models.Model):
    _name = "dms.tag"
    _description = "Document Tag"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(
        default=True,
        help="The active field allows you " "to hide the tag without removing it.",
    )
    category_id = fields.Many2one(
        comodel_name="dms.category",
        string="Category",
        ondelete="set null",
    )
    color = fields.Integer(string="Color Index", default=10)
    directory_ids = fields.Many2many(
        comodel_name="dms.directory",
        relation="dms_directory_tag_rel",
        column1="tid",
        column2="did",
        string="Directories",
        readonly=True,
    )
    file_ids = fields.Many2many(
        comodel_name="dms.file",
        relation="dms_file_tag_rel",
        column1="tid",
        column2="fid",
        string="Files",
        readonly=True,
    )
    company_id = fields.Many2one(
        string='Company',
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.user.company_id
    )

    count_directories = fields.Integer(compute="_compute_count_directories")
    count_files = fields.Integer(compute="_compute_count_files")

    _sql_constraints = [
        ("name_uniq", "unique (name, category_id)", "Tag name already exists!"),
    ]
    auto_added = fields.Boolean(string="Auto Added", default=False)
    type = fields.Selection([
        ('files', 'Files'),
        ('directories', 'Directories'),
    ], required=True)

    @api.depends("directory_ids")
    def _compute_count_directories(self):
        for rec in self:
            rec.count_directories = len(rec.directory_ids)

    @api.depends("file_ids")
    def _compute_count_files(self):
        for rec in self:
            rec.count_files = len(rec.file_ids)
