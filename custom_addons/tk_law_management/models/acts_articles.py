# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _


class ActsArticles(models.Model):
    """Acts Articles"""
    _name = "acts.articles"
    _description = __doc__
    _rec_name = 'name'

    name = fields.Char(string="Name", required=True)
    act_article_no = fields.Char(string="Act/Article Number")
    matter_category_id = fields.Many2one('matter.category', string="Category", required=True)
    matter_sub_category_id = fields.Many2one('matter.sub.category', string="Sub Category",
                                             domain="[('matter_category_id', '=', matter_category_id)]", required=True)
    description = fields.Text(string="Description")

    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )
    
