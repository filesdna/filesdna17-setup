# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_lawyer = fields.Boolean(string="Lawyer",default=False,store=True)
    practise_area_ids = fields.Many2many('law.practise.area', string="Law Selection")

    trial_count = fields.Integer("Trial", compute="_get_trial_count")
    matter_count = fields.Integer("Matter", compute="_get_matter_count")
    is_referral = fields.Boolean(string="Refered By",default=False,store=True)




    def _get_trial_count(self):
        for rec in self:
            trial_count = self.env['court.trial'].search_count([('customer_id', '=', rec.id)])
            rec.trial_count = trial_count

    def action_trial_view(self):
        return {
            'name': _('Trials'),
            'type': 'ir.actions.act_window',
            'res_model': 'court.trial',
            'view_mode': 'tree,form',
            'domain': [('customer_id', '=', self.id)],
            'target': 'current',
        }

    def _get_matter_count(self):
        for rec in self:
            matter_count = self.env['case.matter'].search_count([('customer_id', '=', rec.id)])
            rec.matter_count = matter_count

    def action_matter_view(self):
        return {
            'name': _('Cases'),
            'type': 'ir.actions.act_window',
            'res_model': 'case.matter',
            'view_mode': 'tree,form',
            'domain': [('customer_id', '=', self.id)],
            'target': 'current',
        }



class CrmReferral(models.Model):
    _inherit = "crm.lead"


    referral_id = fields.Many2one(comodel_name='res.partner', string='Refered By')
    
