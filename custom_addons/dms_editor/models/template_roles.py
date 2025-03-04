from odoo import models, fields, api

class TemplateRoles(models.Model):
    _name = 'template.roles'  # Define the model name
    _description = 'Template Roles'  # A brief description of the model

    template_id = fields.Integer(string='Template ID', required=False)  # AllowNull is equivalent to `required=False`
    user_id = fields.Integer(string='User ID', required=False)
    name = fields.Char(string='Name', required=False)
    color = fields.Char(string='Color', required=False)
