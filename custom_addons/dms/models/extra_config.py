from odoo import _, api, fields, models, tools
from random import randint


# class DMSInOut(models.Model):
#     _name = 'dms.in_out'
#     _description = 'In/Out'
#     _order = 'sequence'
#
#
#     def _get_default_color(self):
#         return randint(1, 11)
#
#     name = fields.Char(string='In/Out', required=True)
#     sequence = fields.Integer()
#     color = fields.Integer('Color', default=_get_default_color)
#
#     _sql_constraints = [
#         ('name_uniq', 'unique (name)', "A priority with the same name already exists."),
#     ]
#
#     @api.model
#     def name_create(self, name):
#         existing_tag = self.search([('name', '=ilike', name.strip())], limit=1)
#         if existing_tag:
#             return existing_tag.id, existing_tag.display_name
#         return super().name_create(name)


# class DMSSubject(models.Model):
#     _name = 'dms.subject'
#     _description = 'Subject'
#
#     name = fields.Char(string='Subject', required=True)


# class DMSStatus(models.Model):
#     _name = 'dms.status'
#     _description = 'Status'
#
#     name = fields.Char(string='Status', required=True)


# class DMSFromTo(models.Model):
#     _name = 'dms.from_to'
#     _description = 'From/To'
#
#     name = fields.Char(string='Name', required=True)


# class DMFilePriority(models.Model):
#     _name = 'dms.priority'
#     _description = 'DMS Priority'
#     _order = 'sequence'
#
#     def _get_default_color(self):
#         return randint(1, 11)
#
#     name = fields.Char(required=True, translate=True)
#     sequence = fields.Integer()
#     color = fields.Integer('Color', default=_get_default_color)
#
#     _sql_constraints = [
#         ('name_uniq', 'unique (name)', "A priority with the same name already exists."),
#     ]
#
#     @api.model
#     def name_create(self, name):
#         existing_tag = self.search([('name', '=ilike', name.strip())], limit=1)
#         if existing_tag:
#             return existing_tag.id, existing_tag.display_name
#         return super().name_create(name)


# class DMSType(models.Model):
#     _name = 'dms.type'
#     _description = 'Document Type'
#     _order = "reference"
#
#     name = fields.Char(string='Type Name', required=True)
#     reference = fields.Char()


# class DegreeOfSecrecy(models.Model):
#     _name = 'dms.degree.of.secrecy'
#     _description = 'Degree Of Secrecy'
#     _order = "reference"
#
#     name = fields.Char(string='Type Name', required=True)
#     reference = fields.Char()


class DMSFileUserSelection(models.Model):
    _name = 'dms.file.user.selection'
    _description = 'File User Selection'

    file_id = fields.Many2one('dms.file', string='File', ondelete='cascade')
    user_id = fields.Many2one('res.users', string='User', required=True)
    is_invited = fields.Boolean(string='Invited', default=False)

# class InOut(models.Model):
#     _name = 'in.out'
#     _description = 'In/Out'
#
#     name = fields.Char()