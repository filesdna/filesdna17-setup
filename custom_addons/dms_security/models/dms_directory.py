# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models


class DMSFileSecurity(models.Model):
    _inherit = 'dms.directory'

    dms_security_id = fields.Many2one(comodel_name='dms.security', string='Security Option',compute='onchange_security_user_id', store=True)
    is_security_required  = fields.Boolean('Status',
    related='dms_security_id.is_required',
    readonly=True,
    store=True
    )
    active_security = fields.Boolean('Status',default=False)
    security_user_id = fields.Many2one(comodel_name='res.users', string='Added by',
                related='dms_security_id.user_id',
                readonly=True,
                store=True,
    )

    @api.constrains('active_security')
    def _check_active_security(self):
        for record in self:
            if record.active_security and not record.dms_security_id:
                raise ValidationError("You Have to select security option first.")
                
    @api.depends('active_security')
    def onchange_security_user_id(self):
        for record in self:
            if record.active_security == False:
                record.dms_security_id = False