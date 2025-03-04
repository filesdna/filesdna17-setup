from odoo import models, fields

class BrokerResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    journal_id = fields.Many2one(comodel_name = "account.journal", config_parameter='broker.journal_id', string='Journal')
    cr_account_id = fields.Many2one(comodel_name = 'account.account', config_parameter='broker.cr_account_id',string='Credit Account')
    dr_account_id = fields.Many2one(comodel_name = 'account.account', config_parameter='broker.dr_account_id',string='Debit Account')


    def set_values(self):
        """Set values,
         Returns:
        :return: The result of the superclasses' set_values method.
        """
        res = super(BrokerResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('journal_id', self.journal_id)
        self.env['ir.config_parameter'].sudo().set_param('cr_account_id', self.cr_account_id)
        self.env['ir.config_parameter'].sudo().set_param('dr_account_id', self.dr_account_id)
        return res




