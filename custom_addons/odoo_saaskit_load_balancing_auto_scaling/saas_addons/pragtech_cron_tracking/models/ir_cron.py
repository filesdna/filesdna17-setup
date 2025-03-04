# -*- encoding: utf-8 -*-

import logging
from datetime import datetime
from odoo import api, fields, models, _, sql_db, SUPERUSER_ID, registry

_logger = logging.getLogger(__name__)


class IrCron(models.Model):
    _inherit = "ir.cron"

    start_date = fields.Datetime('Last Cron Start Time')
    end_date = fields.Datetime('Last Cron End Time')
    total_time_taken = fields.Char('Last Cron Total Time Taken (in seconds)')
    total_cron_pass = fields.Integer('Cron Executed Count', default=0)
    total_cron_fail = fields.Integer(
        'Cron Failed Count', compute="_compute_error_log_count")
    last_cron_date = fields.Date('Last Cron Date Executed')
    enable_email_notification = fields.Boolean("Enable Email Notification")
    user_ids = fields.Many2many(
        'res.users', 'ir_cron_user_rel', 'cron_id', 'user_id', 'Users')

    def _compute_error_log_count(self):
        """Compute method to calculate the total error log."""
        for record in self:
            error_log_recs = self.env['cron.error.log'].search_count([
                ('cron_id', '=', record.id)])
            record.total_cron_fail = error_log_recs

    def open_error_logs(self):
        """Method to open the tree view of cron error log."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Error Logs',
            'view_mode': 'tree',
            'res_model': 'cron.error.log',
            'domain': [('cron_id', '=', str(self.id))],
        }

    @api.onchange('enable_email_notification')
    def onchange_enable_email(self):
        """Method to make user_ids as false based on enable_email_notification."""
        for record in self:
            if not record.enable_email_notification:
                record.user_ids = False

    @api.model
    def get_email_to(self):
        """Method to get the all the selected user for the cron."""
        self.ensure_one()
        if self.user_ids:
            email_list = [
                usr.partner_id.email for usr in self.user_ids if usr.partner_id.email]
            return ",".join(email_list)

    @api.model
    def _handle_callback_exception(self, cron_name, server_action_id, job_id, job_exception):
        """Override this method to create the cron error log while cron is
        failed."""
        res = super(IrCron, self)._handle_callback_exception(
            cron_name, server_action_id, job_id, job_exception)
        my_cron = self.browse(job_id)

        cron_error_log_id = self.env['cron.error.log'].sudo().with_context(
            cron_error_status=True).create({
                'name': my_cron.cron_name,
                'method': my_cron._name,
                'object_action': my_cron.code,
                'exec_date': datetime.now(),
                'error_details': str(job_exception),
                'cron_id': str(my_cron.id),
            })

        # set the global parameter that had been used at the time of sending
        # mail
        self.env['ir.config_parameter'].sudo().set_param(
            'pragtech_cron_tracking.cron_id', my_cron.id)

        my_cron.with_context(
            cron_error_log_id=cron_error_log_id.id).action_mail_send()

        return res

    @staticmethod
    def _tracked_crons_history(db, job, start_time, end_time, time_taken):
        """Method to updated all the fields values of cron tracking"""
        lock_cr = db.cursor()
        total_cron_pass = job['total_cron_pass'] + 1

        lock_cr.execute("""UPDATE ir_cron
                                SET start_date = %s,
                                end_date = %s,
                                total_time_taken = %s,
                                total_cron_pass = %s,
                                last_cron_date = %s
                               WHERE id=%s""",
                        (start_time, end_time, time_taken, total_cron_pass,
                         start_time.date(), job['id'],), log_exceptions=False)

        lock_cr.commit()
        return lock_cr

    @classmethod
    def _process_job(cls, db, cron_cr, job):
        """Override this method to add the logic of cron tracking while the
        cron is running."""
        db_registry = registry(cls.pool._db.dbname)

        with db_registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})

            cron_id = env['ir.cron'].browse(job['id'])

            cron_start_time = datetime.now()

            if job['start_date'] != cron_start_time:
                # remove the global parameter, if the cron start time changed.
                env['ir.config_parameter'].sudo().set_param(
                    'pragtech_cron_tracking.cron_id', False)

            try:
                res = super(IrCron, cls)._process_job(db, cron_cr, job)
            finally:
                _logger.debug("released blocks for cron job %s" %
                              job["cron_name"])
            cron_end_time = datetime.now()
            cron_time_taken = cron_end_time - cron_start_time

            # called the function to update the cron tracking record
            tracked_crons = cls._tracked_crons_history(
                db, job, cron_start_time, cron_end_time,
                cron_time_taken.seconds)

            tracked_crons.close()

            cron_id.action_mail_send()  # send the cron status mail

            return res

    def action_mail_send(self):
        """Method to send the cron pass mail to the respective user."""
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']

        get_cron_id = self.env['ir.config_parameter'].sudo().get_param(
            'pragtech_cron_tracking.cron_id')

        current_cron_id = self.env['ir.cron'].search(
            [('id', '=', int(get_cron_id))])

        if self != current_cron_id:
            # call success_cron_mail template
            template_id = ir_model_data._xmlid_to_res_id(
                'pragtech_cron_tracking.cron_pass_email_template')

            if template_id and self.enable_email_notification:
                self.env['mail.template'].browse(template_id).send_mail(
                    self.id, force_send=True)
        elif self._context.get('cron_error_log_id') and current_cron_id:
            # CALL error_log_mail template
            template_id = ir_model_data._xmlid_to_res_id(
                'pragtech_cron_tracking.cron_fail_email_template')

            if template_id and current_cron_id.enable_email_notification:
                self.env['mail.template'].browse(template_id).send_mail(
                    self._context.get('cron_error_log_id'), force_send=True)
