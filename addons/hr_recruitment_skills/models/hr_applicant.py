# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    applicant_skill_ids = fields.One2many('hr.applicant.skill', 'applicant_id', string="Skills")
    skill_ids = fields.Many2many('hr.skill', compute='_compute_skill_ids', store=True)
    is_interviewer = fields.Boolean(compute='_compute_is_interviewer')

    @api.depends_context('uid')
    @api.depends('interviewer_ids', 'job_id.interviewer_ids')
    def _compute_is_interviewer(self):
        is_recruiter = self.user_has_groups('hr_recruitment.group_hr_recruitment_user')
        for applicant in self:
            applicant.is_interviewer = not is_recruiter and self.env.user in (applicant.interviewer_ids | applicant.job_id.interviewer_ids)

    @api.depends('applicant_skill_ids.skill_id')
    def _compute_skill_ids(self):
        for applicant in self:
            applicant.skill_ids = applicant.applicant_skill_ids.skill_id

    def _get_employee_create_vals(self):
        vals = super()._get_employee_create_vals()
        vals['employee_skill_ids'] = [(0, 0, {
            'skill_id': applicant_skill.skill_id.id,
            'skill_level_id': applicant_skill.skill_level_id.id,
            'skill_type_id': applicant_skill.skill_type_id.id,
        }) for applicant_skill in self.applicant_skill_ids]
        return vals

    def _update_employee_from_applicant(self):
        vals_list = []
        for applicant in self:
            existing_skills = applicant.emp_id.employee_skill_ids.skill_id
            skills_to_create = applicant.applicant_skill_ids.skill_id - existing_skills
            vals_list.extend([{
                'employee_id': applicant.emp_id.id,
                'skill_id': skill.id,
                'skill_level_id': applicant.applicant_skill_ids.filtered(lambda s: s.skill_id == skill).skill_level_id.id,
                'skill_type_id': skill.skill_type_id.id,
            } for skill in skills_to_create])
        self.env['hr.employee.skill'].create(vals_list)
        return super()._update_employee_from_applicant()
