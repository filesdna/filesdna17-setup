# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _


class CaseVictim(models.Model):
    """Case Victim"""
    _name = "case.victim"
    _description = __doc__
    _rec_name = 'victim_id'

    avatar = fields.Binary()
    victim_id = fields.Many2one('res.partner', string="Name", required=True)
    phone = fields.Char(string="Phone")
    email = fields.Char(string="Email")
    street = fields.Char(string="Street", translate=True)
    street2 = fields.Char(string="Street 2", translate=True)
    city = fields.Char(string="City", translate=True)
    state_id = fields.Many2one("res.country.state", string='State',
                               domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one("res.country", string="Country")
    zip = fields.Char(string="Zip")
    case_matter_id = fields.Many2one('case.matter')

    @api.onchange('victim_id')
    def victim_details(self):
        for rec in self:
            if rec.victim_id:
                rec.avatar = rec.victim_id.image_1920
                rec.phone = rec.victim_id.phone
                rec.email = rec.victim_id.email
                rec.street = rec.victim_id.street
                rec.street2 = rec.victim_id.street2
                rec.city = rec.victim_id.city
                rec.state_id = rec.victim_id.state_id
                rec.country_id = rec.victim_id.country_id
                rec.zip = rec.victim_id.zip


class CaseFavor(models.Model):
    """Case Favor"""
    _name = "case.favor"
    _description = __doc__
    _rec_name = 'favor_id'

    avatar = fields.Binary()
    favor_id = fields.Many2one('res.partner', string="Name", required=True)
    phone = fields.Char(string="Phone")
    email = fields.Char(string="Email")
    street = fields.Char(string="Street", translate=True)
    street2 = fields.Char(string="Street 2", translate=True)
    city = fields.Char(string="City", translate=True)
    state_id = fields.Many2one("res.country.state", string='State',
                               domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one("res.country", string="Country")
    zip = fields.Char(string="Zip")
    case_matter_id = fields.Many2one('case.matter')

    @api.onchange('favor_id')
    def favor_details(self):
        for rec in self:
            if rec.favor_id:
                rec.avatar = rec.favor_id.image_1920
                rec.phone = rec.favor_id.phone
                rec.email = rec.favor_id.email
                rec.street = rec.favor_id.street
                rec.street2 = rec.favor_id.street2
                rec.city = rec.favor_id.city
                rec.state_id = rec.favor_id.state_id
                rec.country_id = rec.favor_id.country_id
                rec.zip = rec.favor_id.zip


class CaseWitness(models.Model):
    """Case Witness"""
    _name = "case.witness"
    _description = __doc__
    _rec_name = 'witness_id'

    avatar = fields.Binary()
    witness_id = fields.Many2one('res.partner', string="Name", required=True)
    phone = fields.Char(string="Phone")
    email = fields.Char(string="Email")
    street = fields.Char(string="Street", translate=True)
    street2 = fields.Char(string="Street 2", translate=True)
    city = fields.Char(string="City", translate=True)
    state_id = fields.Many2one("res.country.state", string='State',
                               domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one("res.country", string="Country")
    zip = fields.Char(string="Zip")
    case_matter_id = fields.Many2one('case.matter')

    @api.onchange('witness_id')
    def witness_details(self):
        for rec in self:
            if rec.witness_id:
                rec.avatar = rec.witness_id.image_1920
                rec.phone = rec.witness_id.phone
                rec.email = rec.witness_id.email
                rec.street = rec.witness_id.street
                rec.street2 = rec.witness_id.street2
                rec.city = rec.witness_id.city
                rec.state_id = rec.witness_id.state_id
                rec.country_id = rec.witness_id.country_id
                rec.zip = rec.witness_id.zip
