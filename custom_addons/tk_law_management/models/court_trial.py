# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import ValidationError
from odoo import models, fields, api, _


class AccountMove(models.Model):
    """Account Move"""
    _inherit = 'account.move'
    _description = __doc__

    case_matter_id = fields.Many2one('case.matter', string="Case Matter")


class ProjectTask(models.Model):
    """Project Task"""
    _inherit = 'project.task'
    _description = __doc__

    case_matter_id = fields.Many2one('case.matter', string="Case Matter")


class CourtTrial(models.Model):
    """Court Trial"""
    _name = "court.trial"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = __doc__
    _rec_name = 'court_trial'

    court_trial = fields.Char(string="Name", required=True)
    customer_id = fields.Many2one(related='case_matter_id.customer_id', string="Client")
    hearing_date = fields.Datetime(string="Hearing Date", required=True)
    next_hearing_date = fields.Datetime(string="Next Hearing Date")

    judge_id = fields.Many2one('res.users', string="Judge", required=True)
    lawyer_id = fields.Many2one('res.partner', domain=[('is_lawyer', '=', True)], string="Lawyer")
    law_court_id = fields.Many2one('law.court', string="Court")

    trial_charge = fields.Monetary(string="Trial Charge", required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', related="company_id.currency_id")
    invoice_id = fields.Many2one('account.move', string="Invoice")
    payment_state = fields.Selection(related='invoice_id.payment_state', string="Payment State")

    state = fields.Selection([('draft', "Open"), ('close', "Close")], default='draft', string="State")
    case_matter_id = fields.Many2one('case.matter')
    project_id = fields.Many2one('project.project', string="Project")
    task_id = fields.Many2one('project.task', readonly=True, store=True, string="Task")

    def appeal_close(self):
        self.state = 'close'

    def appeal_open(self):
        self.state = 'draft'

    @api.constrains('hearing_date', 'next_hearing_date')
    def _check_law_case_period(self):
        for record in self:
            if record.next_hearing_date and record.hearing_date and record.next_hearing_date < record.hearing_date:
                raise ValidationError("Please ensure the trial next hearing date is greater than the hearing date")

    @api.model
    def default_get(self, fields):
        record = super(CourtTrial, self).default_get(fields)
        if self.env.ref('tk_law_management.case_matter_project'):
            record['project_id'] = self.env.ref('tk_law_management.case_matter_project').id
        else:
            rec = self.env['project.project'].sudo().create({
                'name': 'Case Matter Project',
                'user_id': self.env.user.id,
                'company_id': self.env.company.id,
            })
            record['project_id'] = rec.id
        return record

    def create_task(self):
        service_id = self.env['project.task'].sudo().create({
            'name': self.court_trial,
            'project_id': self.project_id.id,
            'partner_id': self.case_matter_id.customer_id.id,
            'user_ids': self.judge_id.ids,
            'date_deadline': self.hearing_date,
            'case_matter_id': self.case_matter_id.id
        })
        self.task_id = service_id.id

    def case_trial_charge(self):
        for rec in self:
            if not rec.trial_charge:
                message = {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'warning',
                        'message': "Please trial charge can not be zero",
                        'sticky': False,
                    }
                }
                return message
            case_trial_charge = {
                'product_id': self.env.ref('tk_law_management.trial_charge_1').id,
                'name': rec.court_trial,
                'quantity': 1,
                'price_unit': rec.trial_charge,
            }
            invoice_lines = [(0, 0, case_trial_charge)]
            data = {
                'partner_id': rec.customer_id.id,
                'move_type': 'out_invoice',
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': invoice_lines,
                'case_matter_id': rec.case_matter_id.id,
            }
            invoice = self.env['account.move'].sudo().create(data)
            rec.invoice_id = invoice.id
            rec.state = 'close'
