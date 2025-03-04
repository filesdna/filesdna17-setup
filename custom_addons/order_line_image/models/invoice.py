from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    project_id = fields.Many2one(comodel_name='project.project', string='Project Code',
    related='purchase_id.project_id',
    readonly=True,
    store=True
    )
    
    
    
