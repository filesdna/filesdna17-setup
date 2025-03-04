# -*- coding: utf-8 -*-

from odoo import models, fields, api

class PartnerBank(models.Model):

    _inherit = 'res.partner.bank'
    
    ifcs = fields.Char(
        string='IFSC',
    )
    swift_bic = fields.Char(
        string='SWIFT/BIC',
    )
    micr = fields.Char(
        string='MICR Code',
    )
    branch = fields.Char(
        string='Bank Branch Name',
    )
    bank_address = fields.Char(
        string='Bank address',
    )
    routing_code = fields.Char(
        string='Routing Code',
    )
    street = fields.Char(
        string='',
    )
    street2 = fields.Char(
        string='',
    )
    city = fields.Char(
        string='',
    )
    country_id = fields.Many2one(
        'res.country',
        string='',
        )



class PartnerCompanyID(models.Model):

    _inherit = 'res.partner'

    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )
    