
from odoo import api, fields, models


class AbstractDmsMixin(models.AbstractModel):
    _name = "abstract.dms.mixin"
    _description = "Abstract Dms Mixin"

    name = fields.Char(required=True, index=True)
    # Only defined to prevent error in other fields that related it
    storage_id = fields.Many2one(
        comodel_name="dms.storage", string="Storage", store=True, copy=True
    )
    is_hidden = fields.Boolean(
        string="Storage is Hidden",
        related="storage_id.is_hidden",
        readonly=True,
        store=True,
    )
    company_id = fields.Many2one(
        related="storage_id.company_id",
        comodel_name="res.company",
        string="Company",
        readonly=True,
        store=True,
        index=True,
    )
    storage_id_save_type = fields.Selection(related="storage_id.save_type", store=False)
    color = fields.Integer(default=0)
    category_id = fields.Many2one(
        comodel_name="dms.category",
        
        string="Category",
    )

    @api.model
    def search_panel_select_range(self, field_name, **kwargs):
        """Add context to display short folder name."""
        _self = self.with_context(
            directory_short_name=True, skip_sanitized_parent_hierarchy=True
        )
        return super(AbstractDmsMixin, _self).search_panel_select_range(
            field_name, **kwargs
        )

    def _search_panel_sanitized_parent_hierarchy(self, records, parent_name, ids):
        if self.env.context.get("skip_sanitized_parent_hierarchy"):
            all_ids = [value["id"] for value in records]
            # Prevent error if user not access to parent record
            for value in records:
                if value["parent_id"] and value["parent_id"][0] not in all_ids:
                    value["parent_id"] = False
            return records
        return super()._search_panel_sanitized_parent_hierarchy(
            records=records, parent_name=parent_name, ids=ids
        )
