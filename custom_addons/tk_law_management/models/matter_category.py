# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _


class MatterCategory(models.Model):
    """Matter Category"""
    _name = "matter.category"
    _description = __doc__
    _rec_name = 'category'

    category = fields.Char(string="Category", required=True)
    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        default=lambda self: self.env.user.company_id
    )
    


class MatterSubCategory(models.Model):
    """Matter Sub Category"""
    _name = "matter.sub.category"
    _description = __doc__
    _rec_name = 'sub_category'

    sub_category = fields.Char(string="Sub Category", required=True)
    matter_category_id = fields.Many2one('matter.category', string="Category", required=True)
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        related='matter_category_id.company_id',
        readonly=True,
        store=True
        
    )
