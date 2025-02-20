from odoo import models, fields, api


class Project(models.Model):
    _inherit = 'project.project'

    @api.model
    def create(self, vals):
        res = super(Project, self).create(vals)
        create_analytic = self.env['account.analytic.account'].create({
            'name': vals.get('name'),
            'plan_id': 1,
        })
        print('create_analytic=', create_analytic.name)
        res.analytic_account_id = create_analytic.id
        print('setting=', res.analytic_account_id.name)

        return res
