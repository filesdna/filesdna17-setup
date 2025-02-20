# -*- coding: utf-8 -*-

from odoo import models, fields, api


class InvoiceReport(models.Model):

    _inherit = 'account.move'


    lpo  = fields.Char("LPO")
