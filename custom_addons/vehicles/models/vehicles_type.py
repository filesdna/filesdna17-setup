from odoo import models, fields, api



class VehiclesType(models.Model):
    _name = 'vehicles.type'

    name = fields.Char()
