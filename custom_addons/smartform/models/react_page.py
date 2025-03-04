from odoo import models, fields

class SmartformPageHome(models.Model):
    _name = 'smartform.page.home'
    _description = 'Smartform'

    data_path = fields.Char(string= "Data Path")
