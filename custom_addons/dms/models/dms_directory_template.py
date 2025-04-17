from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)


class DmsDirectoryTemplate(models.Model):
    _name = "dms.directory.template"
    _description = "Directory Template"

    name = fields.Char(required=True, string=_("Template Name"))
    line_ids = fields.One2many(
        "dms.directory.template.line", "template_id", string=_("Template Lines")
    )
    # Computed field for displaying the template preview
    preview_hierarchy = fields.One2many(
        "dms.directory.template.line", "template_id",
        compute="_compute_preview_hierarchy", store=False
    )

    @api.depends("line_ids")
    def _compute_preview_hierarchy(self):
        for template in self:
            _logger.info("Computing preview_hierarchy for template: %s", template.name)
            # Build the hierarchy
            tree = defaultdict(list)
            for line in template.line_ids:
                tree[line.parent_id.id].append(line)  # Corrected here

            def build_hierarchy(parent_id=None, level=0):
                """Recursively build the hierarchy."""
                if level > 100:  # Prevent infinite recursion
                    _logger.warning("Maximum recursion depth reached for template: %s", template.name)
                    return self.env["dms.directory.template.line"]
                hierarchy = self.env["dms.directory.template.line"]
                for child in tree.get(parent_id, []):
                    hierarchy += child
                    hierarchy += build_hierarchy(child.id, level + 1)
                return hierarchy

            # Assign the hierarchical recordset to preview_hierarchy
            template.preview_hierarchy = build_hierarchy(None)

    def action_hierarchy(self):
        """Opens the tree view for directory templates."""
        self.ensure_one()  # Ensures the function is executed only for a single record
        return {
            'type': 'ir.actions.act_window',
            'name': _('Directory Templates'),
            'res_model': 'dms.directory.template',
            'view_mode': 'hierarchy',
            'view_id': self.env.ref('dms.action_dms_directory_template_hierarchy').id,
            # 'target': 'current',
            'domain': [('id', '=', self.id)],  # Open only the selected record
        }


class DmsDirectoryTemplateLine(models.Model):
    _name = "dms.directory.template.line"
    _description = "Directory Template Line"
    _order = "sequence, id"
    _parent_name = "parent_id"  # Required for hierarchical tree views

    name = fields.Char(required=True, string=_("Directory Name"), default="New Directory")
    parent_id = fields.Many2one("dms.directory.template.line", string="Parent Directory")
    template_id = fields.Many2one(
        "dms.directory.template", string=_("Directory Template"), ondelete="cascade"
    )
    sequence = fields.Integer(string=_("Sequence"), default=10)
    is_root = fields.Boolean(string="Is Root Directory")
    child_ids = fields.One2many("dms.directory.template.line", "parent_id", string="Child Directories")

    @api.constrains('parent_id')  # Corrected here
    def _check_parent_id(self):    # Renamed method for clarity
        for line in self:
            if line.parent_id and line.parent_id.template_id != line.template_id:
                raise ValidationError(_("Parent directory must belong to the same template."))
