# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import ValidationError
from odoo import models, fields, api, _


class LWADMS(models.Model):

    _inherit = 'dms.file'


    case_matter_id = fields.Many2one(
        'case.matter',
        string='Case',
        )

class LWADMS(models.Model):

    _inherit = 'dms.directory'


    state_id = fields.Many2one("res.country.state", string='State')



class MatterDMSLine(models.Model):

    _name = 'case.matter.dms.line'
    _description = 'Add document page'

    case_matter_id = fields.Many2one(comodel_name='case.matter', string='Case')
    document_id =  fields.Many2one(comodel_name='dms.file', string='File')
    matter_document_type_id =  fields.Many2one(comodel_name='case.matter.document.type', string='Type')
    attachment_ids = fields.Many2many(comodel_name='ir.attachment', string='File')
    date = fields.Datetime(string="Date", )
    description = fields.Html()


class MatterDMSLine(models.Model):

    _name = 'case.matter.document.type'
    _description = 'Case Document document type'

    name = fields.Char("Type")
    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )
    
