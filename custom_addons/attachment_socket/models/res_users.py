from odoo import models, fields, api



class ResUsersAuth(models.Model):

    _inherit = 'res.users'



    @api.model
    def create(self, values):
        result = super(ResUsersAuth, self).create(values)
        self.env['auth.token'].cron_update_tokens()
        return result