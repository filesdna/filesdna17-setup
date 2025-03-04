# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import ValidationError
from odoo import models, fields, api, _


class CaseMatter(models.Model):
    """Case Matter"""
    _name = "case.matter"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = __doc__
    _rec_name = 'sequence_number'

    sequence_number = fields.Char(string='Sequence No', readonly=True, default=lambda self: _('New'), copy=False)
    case_matter = fields.Char(string="Case", required=True)
    customer_id = fields.Many2one("res.partner", string="Client", required=True)
    referral_id = fields.Many2one(comodel_name='res.partner', string='Refered By')
    phone = fields.Char(string="Phone")
    email = fields.Char(string="Email")
    street = fields.Char(string="Street", translate=True)
    street2 = fields.Char(string="Street 2", translate=True)
    city = fields.Char(string="City", translate=True)
    state_id = fields.Many2one("res.country.state", string='State',
                               domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one("res.country", string="Country")
    zip = fields.Char(string="Zip")

    case_state_id = fields.Many2one("res.country.state", string='Case State',
                               domain="[('country_id', '=?', country_id)]")
    case_country_id = fields.Many2one("res.country", string="Case Country")
    open_date = fields.Date(string="Open Date", required=True)
    close_date = fields.Date("Expected Close Date", required=True)
    matter_category_id = fields.Many2one('matter.category', string="Category", required=True)
    matter_sub_category_id = fields.Many2one('matter.sub.category', string="Sub Category",
                                             domain="[('matter_category_id', '=', matter_category_id)]", required=True)
    state = fields.Selection([('draft', "Draft"), ('open', "Open"), ('close', "Close"), ('pending', "Pending")],
                             string="Status", default="draft", group_expand='_expand_groups')

    case_evidence_ids = fields.One2many('case.evidence', 'case_matter_id', string="Evidence")
    acts_articles_ids = fields.Many2many('acts.articles', string="Acts / Articles")
    court_trial_ids = fields.One2many('court.trial', 'case_matter_id', string="Trial")

    trial_count = fields.Integer(" Trial", compute="_compute_trial_count")
    sub_case_count = fields.Integer(" Trial", compute="_compute_sub_case_count")
    act_article_count = fields.Integer(" Acts / Articles", compute="_compute_act_article_count")

    customer_lead_id = fields.Many2one('crm.lead', compute="_compute_customer_lead_matter", string="Lead")
    case_matter_document_id = fields.Many2one('case.matter.document', string="Documents")
    document_count = fields.Integer(compute='_compute_document_count')
    case_victim_ids = fields.One2many('case.victim', 'case_matter_id', string="Victims")
    case_favor_ids = fields.One2many('case.favor', 'case_matter_id', string="Favors")
    case_witness_ids = fields.One2many('case.witness', 'case_matter_id', string="Witness")
    matter_details = fields.Text(string="Case Details")
    task_count = fields.Integer(compute='_task_count', string="Task")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', related="company_id.currency_id")
    dms_line_ids = fields.One2many(comodel_name='case.matter.dms.line', inverse_name='case_matter_id', string='DMS')
    ref_number = fields.Char("Refereance Number")
    sub_case_id = fields.Many2one(
        string="Sub Case",
        comodel_name="case.matter",
        ondelete="set null",
        readonly=True
    )
    locked  = fields.Boolean("",default=False)


    def upload_document(self):
        for record in self:
            folder = self.env['dms.directory'].search([('name','=',record.case_state_id.name)],
            limit=1
            )
            return{
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'res_model': 'dms.file',
                    'name': _("Add File"),
                    'views': [(False, 'form')],
                    'context': {
                        'default_case_matter_id': record.id,
                        'default_document_model' : 'matter',
                        'default_directory_id' : folder.id
                             },
                }
    @api.model
    def _expand_groups(self, states, domain, order):
        return ['draft', 'open', 'pending', 'close']

    @api.constrains('open_date', 'close_date')
    def _check_law_time_period(self):
        for record in self:
            if record.close_date and record.open_date and record.close_date < record.open_date:
                raise ValidationError("Please ensure the case expected close date is greater than the open date")

    def draft_to_open(self):
        self.state = 'open'

    def open_to_close(self):
        self.ensure_one()
        template_id = self.env.ref("tk_law_management.case_matter_close_mail_template").sudo()
        ctx = {
            'default_model': 'case.matter',
            'default_res_ids': self.ids,
            'default_partner_ids': [self.customer_id.id],
            'default_use_template': bool(template_id),
            'default_template_id': template_id.id,
            'default_composition_mode': 'comment',
            'default_email_from': self.env.company.email,
            'default_reply_to': self.env.company.email,
            'custom_layout': False,
            'force_email': True,
        }
        self.state = 'close'
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    def close_to_pending(self):
        self.state = 'pending'

    def case_re_open(self):
        self.state = 'draft'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('sequence_number', _('New')) == _('New'):
                vals['sequence_number'] = self.env['ir.sequence'].next_by_code('case.matter') or _('New')
        res = super(CaseMatter, self).create(vals_list)
        return res

    def _compute_customer_lead_matter(self):
        customer_lead_id = self.env['crm.lead'].search([('case_matter_id', '=', self.id)], limit=1)
        self.customer_lead_id = customer_lead_id.id

    @api.onchange('customer_id')
    def customer_details(self):
        for rec in self:
            if rec.customer_id:
                rec.phone = rec.customer_id.phone
                rec.email = rec.customer_id.email
                rec.street = rec.customer_id.street
                rec.street2 = rec.customer_id.street2
                rec.city = rec.customer_id.city
                rec.state_id = rec.customer_id.state_id
                rec.country_id = rec.customer_id.country_id
                rec.zip = rec.customer_id.zip

    def _task_count(self):
        for rec in self:
            task_count = self.env['project.task'].search_count([('case_matter_id', '=', rec.id)])
            rec.task_count = task_count

    def action_task_view(self):
        return {
            'name': _('Tasks'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'tree,form',
            'domain': [('case_matter_id', '=', self.id)],
            'target': 'current',
            'context': {
                'create': False
            }
        }

   
    def _compute_trial_count(self):
        for rec in self:
            trials = self.env['court.trial'].search_count([('case_matter_id', '=', rec.id)])
            rec.trial_count = trials

    def _compute_sub_case_count(self):
        for rec in self:
            sub_case = self.env['case.matter'].search_count([('sub_case_id', '=', rec.id)])
            rec.sub_case_count = sub_case

    def action_trial_view(self):
        return {
            'name': _('Trials'),
            'type': 'ir.actions.act_window',
            'res_model': 'court.trial',
            'view_mode': 'tree,form',
            'domain': [('case_matter_id', '=', self.id)],
            'contex': {
                'default_case_matter_id': self.id,
                'default_customer_id': self.customer_id.id,
                'create': False
            },
            'target': 'current',
        }

    def _compute_act_article_count(self):
        self.act_article_count = len(self.acts_articles_ids)

    def action_act_article_view(self):
        return {
            'name': _('Acts / Articles'),
            'type': 'ir.actions.act_window',
            'res_model': 'acts.articles',
            'domain': [('id', 'in', self.acts_articles_ids.ids)],
            'view_mode': 'tree,form',
            'target': 'current',
            'context': {
                'create': False
            }
        }

    def _compute_document_count(self):
        for rec in self:
            document_count = self.env['dms.file'].search_count([('case_matter_id', '=', rec.id)])
            rec.document_count = document_count
        return True

    def action_case_matter_document(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Documents'),
            'res_model': 'dms.file',
            'domain': [('case_matter_id', '=', self.id)],
            'context': {'default_case_matter_id': self.id,'create': False},
            'view_mode': 'kanban,form',
            'target': 'current',
        }

    def action_sub_case(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('SUB Cases'),
            'res_model': 'case.matter',
            'domain': [('sub_case_id', '=', self.id)],
            'context': {'create': False},
            'view_mode': 'tree,form',
            'target': 'current',
        }
