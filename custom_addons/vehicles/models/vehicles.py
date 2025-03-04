from odoo import models, fields, api


class Vehicles(models.Model):
    _name = 'vehicles'

    name = fields.Char()
    code = fields.Char()
    employee_id = fields.Many2one('hr.employee')
    employee_ids = fields.One2many('hr.employee', 'vehicles_id')
    vehicles_type = fields.Many2one('vehicles.type')

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            if self.employee_id not in self.employee_ids:
                self.employee_ids = [(4, self.employee_id.id)]
