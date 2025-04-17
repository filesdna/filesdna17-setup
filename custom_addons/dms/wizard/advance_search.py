from odoo import _, api, fields, models, tools
from markupsafe import Markup
from datetime import datetime
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError


class AdvanceSearch(models.Model):
    _name = "advance.search"

    # ----------------------------------------------
    date_start = fields.Date(string='Start Date')
    date_end = fields.Date(string='Expiration Date', index=True, tracking=True,
                           help="Date on which this project ends. The timeframe defined on the project is taken into account when viewing its planning.")

    tag_ids = fields.Many2many("dms.tag")
    created_by = fields.Many2one('res.users', string="Created By")
    edite_by = fields.Many2one('res.users', string="Edited By")
    reference = fields.Integer()
    operator = fields.Selection([
        ('and', 'And'),
        ('or', 'Or'),
    ], )
    parameter_values = fields.One2many('dms.link.document.parameter.line', 'advance_id', string="Document Parameters")

    # ------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------

    @api.model
    def default_get(self, fields_list):
        """ Auto-populate parameters when creating a new document """
        res = super(AdvanceSearch, self).default_get(fields_list)
        parameters = self.env['document.parameters'].search([])
        print('parameters=', parameters)
        res['parameter_values'] = [
            (0, 0, {'parameter_id': param.id}) for param in parameters
        ]
        print('res=', res)
        return res

    def action_search(self):
        print('action_search')
        if not self.date_start:
            raise ValidationError("Add The Date From And The Date To")
        domain = []

        if self.date_start:
            domain.append(('create_date', '>=', self.date_start))
            domain.append(('create_date', '<=', self.date_end))

        if self.tag_ids:
            domain.append(('tag_ids', '=', self.tag_ids.ids))

        if self.created_by:
            domain.append(('create_uid', '=', self.created_by.id))

        if self.edite_by:
            domain.append(('write_uid', '=', self.edite_by.id))

        if self.reference:
            domain.append(('total', '=', self.reference))

        if self.operator == 'and':
            domain.append(('tag_ids', 'in', self.tag_ids.ids))
            for tag_id in self.tag_ids.ids:
                domain.append(('tag_ids', '=', tag_id))
        elif self.operator == 'or':
            domain.append(('tag_ids', '=', self.tag_ids.ids))

        if self.parameter_values.selected_value_id:
            for parm in self.parameter_values.selected_value_id:
                domain.append(('parameter_values.selected_value_id', '=', parm.ids))
        # add each search in one line

        print('domain=', domain)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Search DMS Files',
            'res_model': 'dms.file',
            'view_mode': 'tree',
            'view_id': self.env.ref('dms.view_dms_file_tree').id,
            'domain': domain,
            'context': dict(self.env.context, create=False),
        }
