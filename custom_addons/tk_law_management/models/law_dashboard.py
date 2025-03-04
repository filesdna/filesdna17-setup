# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _


class LawDashboard(models.Model):
    _name = "law.dashboard"
    _description = "Law Dashboard"

    @api.model
    def get_law_dashboard(self):
        case_matter = self.env['case.matter'].sudo().search_count([('company_id','=',self.env.user.company_id.id)])
        open_case_matter = self.env['case.matter'].sudo().search_count([('state', '=', 'open'),('company_id','=',self.env.user.company_id.id)])
        pending_case_matter = self.env['case.matter'].sudo().search_count([('state', '=', 'pending'),('company_id','=',self.env.user.company_id.id)])
        close_case_matter = self.env['case.matter'].sudo().search_count([('state', '=', 'close'),('company_id','=',self.env.user.company_id.id)])
        law_practise_area = self.env['law.practise.area'].sudo().search_count([('company_id','=',self.env.user.company_id.id)])
        matter_category = self.env['matter.category'].sudo().search_count([('company_id','=',self.env.user.company_id.id)])
        law_court = self.env['law.court'].sudo().search_count([('company_id','=',self.env.user.company_id.id)])
        case_judge = self.env['res.users'].sudo().search_count([('company_id','=',self.env.user.company_id.id)])
        case_lawyer = self.env['res.partner'].sudo().search_count([('is_lawyer', '=', True),('company_id','=',self.env.user.company_id.id)])

        case_matter_status = [['Open', 'Pending', 'Close'], [open_case_matter, pending_case_matter, close_case_matter]]
        over_all_info = [['Judges', 'Lawyers'], [case_judge, case_lawyer]]

        data = {
            'case_matter': case_matter,
            'open_case_matter': open_case_matter,
            'pending_case_matter': pending_case_matter,
            'close_case_matter': close_case_matter,
            'law_practise_area': law_practise_area,
            'matter_category': matter_category,
            'law_court': law_court,
            'case_judge': case_judge,
            'case_lawyer': case_lawyer,
            'case_matter_status': case_matter_status,
            'over_all_info': over_all_info,
        }
        return data
