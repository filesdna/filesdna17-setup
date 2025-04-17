from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    enable_basic = fields.Boolean(
        string="My Boolean Field",
        store=True,
    )

    @api.model
    def get_values(self):
        """ Load stored settings from config parameters. """
        res = super().get_values()


        res.update({
            "enable_basic": self.env["ir.config_parameter"].sudo().get_param("hr_advanced.enable_basic", default="False") == "True",
        })
        return res

    def set_values(self):
        """ Save user-configured values to config parameters. """
        super().set_values()
        params = self.env["ir.config_parameter"].sudo()

        params.set_param("hr_advanced.enable_basic", "True" if self.enable_basic else "False")

        hide_enable_basic = self.env.ref('hr_advanced.group_hr_grade_salary', raise_if_not_found=False)
        if self.enable_basic:
            if hide_enable_basic not in self.env.user.groups_id:
                self.env.user.groups_id = [(4, hide_enable_basic.id)]
        else:
            if hide_enable_basic:
                self.env.user.groups_id = [(3, hide_enable_basic.id)]