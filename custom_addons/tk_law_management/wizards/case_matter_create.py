# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import ValidationError
from odoo import models, fields, api, _


class CustomerLead(models.Model):
    """Customer Lead"""
    _inherit = "crm.lead"
    _description = __doc__

    case_matter_id = fields.Many2one('case.matter', string="Case")


class CaseMatterCreate(models.TransientModel):
    """Case Matter Create"""
    _name = 'case.matter.create'
    _description = __doc__

    matter_category_id = fields.Many2one('matter.category', string="Category")
    matter_sub_category_id = fields.Many2one('matter.sub.category', string="Sub Category",
                                             domain="[('matter_category_id', '=', matter_category_id)]")
    open_date = fields.Date(string="Open Date")
    close_date = fields.Date(string="Expected Close Date")
    case_matter_id = fields.Many2one('case.matter', string="Case")
    crm_lead_id = fields.Many2one('crm.lead', string="Lead")
    state_id = fields.Many2one("res.country.state", string='Case State',
                               domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one("res.country", string="Case Country")

    @api.constrains('open_date', 'close_date')
    def _check_law_time_period(self):
        for record in self:
            if record.close_date and record.open_date and record.close_date < record.open_date:
                raise ValidationError("Please ensure the case expected close date is greater than the open date")

    def case_matter_details(self):
        crm_lead_id = self.env['crm.lead'].browse(self._context.get('active_id'))
        if not crm_lead_id.partner_id:
            message = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': "Please, first select the customer!",
                    'sticky': False,
                }
            }
            return message
        data = {
            'case_matter': crm_lead_id.name,
            'customer_id': crm_lead_id.partner_id.id,
            'matter_category_id': self.matter_category_id.id,
            'matter_sub_category_id': self.matter_sub_category_id.id,
            'open_date': self.open_date,
            'close_date': self.close_date,
            'case_state_id':self.state_id.id,
            'case_country_id':self.country_id.id,
            'referral_id':crm_lead_id.referral_id.id
        }
        case_matter_id = self.env['case.matter'].create(data)
        crm_lead_id.case_matter_id = case_matter_id.id
        case_matter_id.customer_details()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Case'),
            'res_model': 'case.matter',
            'res_id': case_matter_id.id,
            'view_mode': 'form',
            'target': 'current'
        }
