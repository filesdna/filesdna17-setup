##############################################################################
#
#    Copyright Domiup (<http://domiup.com>).
#
##############################################################################

from odoo import fields, models


class MultiApprovalTypeLine(models.Model):
    _inherit = "multi.approval.type.line"

    group_ids = fields.Many2many(string="Deputy Groups", comodel_name="res.groups")
    _sql_constraints = [
        ("name_uniq", "unique (name, type_id)", "Each name must be unique."),
    ]
