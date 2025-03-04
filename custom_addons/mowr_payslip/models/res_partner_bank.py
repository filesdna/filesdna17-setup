# -*- coding: utf-8 -*-

from odoo import models, fields, api

class PartnerBank(models.Model):

    _inherit = 'res.bank'


    payer_account = fields.Char(
        string='Payer Account',
     
    )
    swift_bic = fields.Char(
        string='Receiver BIC',
     
    )
    