from datetime import date, datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ScrapProperty(models.Model):

    _name = 'scrap.property'
    _description = 'Scrap Property'

    name = fields.Char()
    custody_property = fields.Many2one('custody.property')

