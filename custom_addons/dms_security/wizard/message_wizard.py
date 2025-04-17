from odoo import models, fields, api


class MessageWizard(models.TransientModel):
    _name = 'message.wizard'

    message = fields.Text('Message', required=True, readonly=True)

    @api.model
    def action_ok(self):
        """ close wizard"""
        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def reload(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
