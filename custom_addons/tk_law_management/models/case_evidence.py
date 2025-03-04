# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _


class CaseEvidence(models.Model):
    """Case Evidence"""
    _name = "case.evidence"
    _description = __doc__
    _rec_name = 'evidence_name'

    avatar = fields.Binary(string="Avatar")
    case_matter_id = fields.Many2one('case.matter')
    customer_id = fields.Many2one(related='case_matter_id.customer_id', string="Client")
    evidence_name = fields.Char(string="Evidence", required=True)
    case_favor_ids = fields.One2many(related="case_matter_id.case_favor_ids")
    case_favor_id = fields.Many2one('case.favor', string="In Favor", required=True,
                                    domain="[('id', 'in', case_favor_ids)]")
    description = fields.Char(string="Description")

    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )
    
