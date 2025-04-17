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

    parameter_values = fields.One2many('dms.link.document.parameter.line', 'advance_id', string="Document Parameters")

    # ------------------------------------------------------------------------------
    selector_date = fields.Selection([
        ('date', 'Date'),
        ('reference', 'Reference'),
        ('tag', 'Tag'),
        ('parameter', 'Parameter'),
        ('created_by', 'Created By'),
        ('write_by', 'Edited By'),
    ], )
    selector_tag = fields.Selection([
        ('date', 'Date'),
        ('reference', 'Reference'),
        ('tag', 'Tag'),
        ('parameter', 'Parameter'),
        ('created_by', 'Created By'),
        ('write_by', 'Edited By'),
    ], )
    selector_reference = fields.Selection([
        ('date', 'Date'),
        ('reference', 'Reference'),
        ('tag', 'Tag'),
        ('parameter', 'Parameter'),
        ('created_by', 'Created By'),
        ('write_by', 'Edited By'),
    ], )
    selector_created_by = fields.Selection([
        ('date', 'Date'),
        ('reference', 'Reference'),
        ('tag', 'Tag'),
        ('parameter', 'Parameter'),
        ('created_by', 'Created By'),
        ('write_by', 'Edited By'),
    ], )
    selector_edite_by = fields.Selection([
        ('date', 'Date'),
        ('reference', 'Reference'),
        ('tag', 'Tag'),
        ('parameter', 'Parameter'),
        ('created_by', 'Created By'),
        ('write_by', 'Edited By'),
    ], )
    selector_parameter = fields.Selection([
        ('date', 'Date'),
        ('reference', 'Reference'),
        ('tag', 'Tag'),
        ('parameter', 'Parameter'),
        ('created_by', 'Created By'),
        ('write_by', 'Edited By'), ], )
    # --------------------------------------------------------
    operator_1 = fields.Selection([
        ('and', 'And'),
        ('or', 'Or'),
    ], )
    operator_2 = fields.Selection([
        ('and', 'And'),
        ('or', 'Or'),
    ], )
    operator_3 = fields.Selection([
        ('and', 'And'),
        ('or', 'Or'),
    ], )
    operator_4 = fields.Selection([
        ('and', 'And'),
        ('or', 'Or'),
    ], )
    operator_5 = fields.Selection([
        ('and', 'And'),
        ('or', 'Or'),
    ], )
    operator_6 = fields.Selection([
        ('and', 'And'),
        ('or', 'Or'),
    ], )
    operator_tag = fields.Selection([
        ('and', 'And'),
        ('or', 'Or'),
    ], )

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
        domain = []
        if self.operator_1 == 'or':
            domain.append('|')
        if self.operator_2 == 'or':
            domain.append('|')
        if self.operator_3 == 'or':
            domain.append('|')
        if self.operator_4 == 'or':
            domain.append('|')
        if self.operator_5 == 'or':
            domain.append('|')
        if self.operator_6 == 'or':
            domain.append('|')
        # if self.operator_tag == 'or':
        #     domain.append('|')
        # else:
        #     domain.append()
        if any(operator == 'or' for operator in
               [self.operator_1, self.operator_2, self.operator_3, self.operator_4, self.operator_5, self.operator_6]):
            print('selector or')
            if self.date_start and self.date_end:
                domain.append('&')
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

            if self.operator_tag == 'and':
                domain.append(('tag_ids', 'in', self.tag_ids.ids))
                for tag_id in self.tag_ids.ids:
                    domain.append(('tag_ids', '=', tag_id))
            elif self.operator_tag == 'or':
                domain.append(('tag_ids', '=', self.tag_ids.ids))

            if self.parameter_values.selected_value_id:
                for parm in self.parameter_values.selected_value_id:
                    domain.append(('parameter_values.selected_value_id', '=', parm.ids))

        if any(operator == 'and' for operator in
               [self.operator_1, self.operator_2, self.operator_3, self.operator_4, self.operator_5, self.operator_6]):
            print('selector and')
            if self.date_start and self.date_end:
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

            if self.operator_tag == 'and':
                domain.append(('tag_ids', 'in', self.tag_ids.ids))
                for tag_id in self.tag_ids.ids:
                    domain.append(('tag_ids', '=', tag_id))
            elif self.operator_tag == 'or':
                domain.append(('tag_ids', '=', self.tag_ids.ids))

            if self.parameter_values.selected_value_id:
                for parm in self.parameter_values.selected_value_id:
                    domain.append(('parameter_values.selected_value_id', '=', parm.ids))

        if not any(operator in ['or', 'and'] for operator in
                   [self.operator_1, self.operator_2, self.operator_3, self.operator_4, self.operator_5,
                    self.operator_6]):
            print('Others')
            if self.date_start and self.date_end:
                domain.append(('create_date', '>=', self.date_start))
                domain.append(('create_date', '<=', self.date_end))

            if self.tag_ids:
                domain.append(('tag_ids', 'in', self.tag_ids.ids))

            if self.created_by:
                domain.append(('create_uid', '=', self.created_by.id))

            if self.edite_by:
                domain.append(('write_uid', '=', self.edite_by.id))

            if self.reference:
                domain.append(('total', '=', self.reference))

            if self.operator_tag == 'and':
                domain.append(('tag_ids', 'in', self.tag_ids.ids))
                for tag_id in self.tag_ids.ids:
                    domain.append(('tag_ids', '=', tag_id))
            elif self.operator_tag == 'or':
                domain.append(('tag_ids', '=', self.tag_ids.ids))

            if self.parameter_values.selected_value_id:
                for parm in self.parameter_values.selected_value_id:
                    domain.append(('parameter_values.selected_value_id', '=', parm.ids))

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

    def action_cancel(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Files',
            'res_model': 'dms.file',
            'view_mode': 'tree',
            'target': 'current',
            'context': {
                'action': self.env.ref('dms.action_dms_file').id
            },
        }
