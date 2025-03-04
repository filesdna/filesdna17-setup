from odoo import fields, models, api


class ResConfigInherit(models.TransientModel):
    _inherit = 'res.config.settings'
    # _inherits = {'res.config.settings': 'billing'}

    billing = fields.Selection(selection_add=[('user_plan_price', 'Users + Plan Price')
                                              ], string="Billing Type", default="normal")
    plan_users = fields.Integer(readonly=False, string="Default Plan Users", config_parameter="plan_users")
    manual = fields.Boolean(string="Manual", config_parameter="billing_type_extension.manual")
    automated = fields.Boolean(string="Automated", config_parameter='billing_type_extension.automated')
    based_on = fields.Selection([('phone_number', 'Phone Number'), ('tax_number', 'Tax Number')], config_parameter="billing_type_extension.based_on")
    language_id = fields.Many2one('res.lang',config_parameter="billing_type_extension.language_id",domain=[('active', 'in', [True, False])])


    @api.onchange('manual')
    def _onchange_manual(self):
        for record in self:
            if record.manual:
                record.automated = False
                record.based_on = None

    @api.onchange('automated')
    def _onchange_automated(self):
        for record in self:
            if record.automated:
                record.manual = False

    @api.model
    def default_get(self, fields_list):
        res = super(ResConfigInherit, self).default_get(fields_list)
        ICPSudo = self.env['ir.config_parameter'].sudo()
        values = {
            'plan_users': ICPSudo.search([('key', '=', 'plan_users')]).value,
        }
        res.update(values)

        return res

    def set_values(self):
        res = super(ResConfigInherit, self).set_values()
        self.set_configs('plan_users', self.plan_users or False)
        return res
