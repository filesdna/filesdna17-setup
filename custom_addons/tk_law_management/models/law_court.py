# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _


class LawCourt(models.Model):
    """Law Court"""
    _name = "law.court"
    _description = __doc__
    _rec_name = 'name'

    name = fields.Char(string="Court", required=True)
    street = fields.Char(string="Street", translate=True)
    street2 = fields.Char(string="Street 2", translate=True)
    city = fields.Char(string="City", translate=True)
    state_id = fields.Many2one("res.country.state", string='State',
                               domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one("res.country", string="Country")
    zip = fields.Char(string="Zip")
    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )
    
