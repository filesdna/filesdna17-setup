from odoo import models, fields, api


class Picking(models.Model):
    _inherit = 'stock.picking'

    employee_id = fields.Many2one('hr.employee')
    sign_employee_id = fields.Binary(related='employee_id.sign')

    def action_sign(self):
        self.employee_id = self.env.user.employee_id.id
        print('action_sign')
        print('test=', self.env.user.employee_id.id)

