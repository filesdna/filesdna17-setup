# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class NameModel(models.Model):
    _inherit = 'project.task'

    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note"),
    ], default=False)

    progress = fields.Float(string='Progress', compute='_compute_progress')
    completed_tasks = fields.Integer(string='Completed Tasks', compute='_compute_task_summary')
    total_tasks = fields.Integer(string='Total Tasks', compute='_compute_task_summary')

    @api.depends('child_ids', 'child_ids.progress', 'child_ids.state')
    def _compute_progress(self):
        for record in self:
            if not record.child_ids:
                record.progress = 100 if record.state == '1_done' else 0
            else:
                total_progress = 0
                done_count = 0
                for child in record.child_ids:
                    total_progress += child.progress
                    if child.state == '1_done':
                        done_count += 1
                num_children = len(record.child_ids)
                record.progress = total_progress / num_children if num_children else 0

                if num_children and done_count == num_children:
                    record.state = '1_done'

    @api.depends('child_ids', 'child_ids.state')
    def _compute_child_state(self):
        for record in self:
            for child in record.child_ids:
                if child.state == "1_done":
                    for ch in child.child_ids:
                        ch.state = '1_done'


class ProjectProject(models.Model):
    _inherit = 'project.project'

    task_ids = fields.One2many('project.task', 'project_id', string='Tasks')
    task_progress = fields.Float(string="Task Progress", compute="_compute_task_progress")

    # overall_progress = fields.Float(string='Overall Progress', compute='_compute_task_progress')

    @api.depends('task_ids')
    def _compute_task_progress(self):
        for project in self:
            total = 0.0
            count = 0

            # Use a direct search instead of relying on project.task_ids
            tasks = self.env['project.task'].search([
                ('project_id', '=', project.id),
                ('parent_id', '=', False),
                ('state', '!=', '1_canceled'),
            ])

            print(f"📌 Found {len(tasks)} main tasks for project: {project.name}")

            for task in tasks:
                progress = 100.0 if task.state == '1_done' else (task.progress or 0.0)
                total += progress
                count += 1

            project.task_progress = round(total / count, 2) if count else 0.0
