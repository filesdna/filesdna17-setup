from odoo import models, fields

class WorkflowPageHome(models.Model):
    _name = 'workflow.page.home'
    _description = 'Workflow'
    _inherit = ['mail.thread', 'mail.activity.mixin']

class WorkflowPageApprovals(models.Model):
    _name = 'workflow.page.approvals'
    _description = 'Workflow'
    _inherit = ['mail.thread', 'mail.activity.mixin']

class WorkflowPageAssigned(models.Model):
    _name = 'workflow.page.assigned'
    _description = 'Workflow'
    _inherit = ['mail.thread', 'mail.activity.mixin']