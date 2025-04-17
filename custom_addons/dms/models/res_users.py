# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import hashlib


class ResUsers(models.Model):
    _inherit = 'res.users'

    encription_key = fields.Char(string='Encription Key', related='company_id.encription_key', readonly=True,
                                 store=True)
    encription_type = fields.Selection(string='Encription Type', selection=[('user', 'User'), ('company', 'Company'), ],
                                       default='user')
    is_auto_lock = fields.Boolean(string='Auto Lock Fiels', default=False)

    access_id_many = fields.Many2many('dms.access.group', store=True)

    access_id = fields.Many2one('dms.access.group', store=True)

    perm_access = fields.Many2many('document.parameters.line', compute='_compute_perm_access', store=False, index=True)
    perm_domain = fields.Char(store=True, index=True)

    @api.onchange('access_id_many')
    def _compute_perm_access(self):
        for record in self:
            all_selected_value_ids = []
            selected_value_to_parameter = {}

            # Iterate through all access groups in access_id_many
            for access_group in record.access_id_many:
                perms = access_group.parameter_values_access
                for perm in perms:
                    for selected_value in perm.selected_value_ids:
                        # Collect only the integer ID of the selected value
                        all_selected_value_ids.append(selected_value.id)
                        parameter_id = selected_value.document_parameters.id
                        selected_value_to_parameter[selected_value.id] = parameter_id

            # Remove duplicates by converting to a set and back to a list
            all_selected_value_ids = list(set(all_selected_value_ids))
            record.perm_access = [(6, 0, all_selected_value_ids)]

            # Prepare the perm_domain
            if record.perm_access:
                record.perm_domain = '[{}]'.format(','.join(map(str, record.perm_access.ids)))
            else:
                record.perm_domain = ''

    # -----------------------For One Access-----------------------------
    access_id = fields.Many2one('dms.access.group')

    perm_create = fields.Boolean(related='access_id.perm_create')
    perm_delete = fields.Boolean(related='access_id.perm_unlink')
    # @api.onchange('access_id.parameter_values_access')
    # def _compute_perm_access(self):
    #     for record in self:
    #         all_selected_value_ids = []
    #         selected_value_to_parameter = {}
    #         perms = record.access_id.parameter_values_access
    #         for perm in perms:
    #             for selected_value in perm.selected_value_ids:
    #                 all_selected_value_ids.append(selected_value.id)
    #                 parameter_id = selected_value.document_parameters.id
    #                 selected_value_to_parameter[selected_value.id] = parameter_id
    #         all_selected_value_ids = sorted(set(all_selected_value_ids))
    #         record.perm_access = [(6, 0, all_selected_value_ids)]
    #         grouped_output = {}
    #         for selected_value_id, parameter_id in selected_value_to_parameter.items():
    #             if parameter_id not in grouped_output:
    #                 grouped_output[parameter_id] = []
    #             grouped_output[parameter_id].append(selected_value_id)
    #             if record.perm_access:
    #                 record.perm_domain = '[{}]'.format(','.join(map(str, record.perm_access.ids)))
    #             else:
    #                 record.perm_domain = ''
            # formatted_output = []
            # for value_ids in grouped_output.values():
            #     formatted_output.append(f"[{','.join(map(str, value_ids))}]")
            # output_string = " and ".join(formatted_output)
            # record.perm_domain = output_string
            # print('Formatted Output:', output_string)
