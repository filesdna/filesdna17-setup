# -*- coding: utf-8 -*-
{
    'name': "Cron Tracking and Failure Notification",
    'version': '17.0.0.0',
    'author': 'Pragmatic TechSoft Pvt Ltd.',
    'website': 'http://www.pragtech.co.in',
    'category': 'Extra Tools',
    'summary': """
        Cron Tracking & Cron jobs/Scheduled Actions failure Log Notification
    """,
    'description': """
        This module will generate error Logs for Scheduled
        Actions / Cron jobs running in backend server and tracked the crons
    """,
    'depends': ['base', 'mail', 'web', 'base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'views/cron_error_log_views.xml',
        'views/ir_cron_views.xml',
        'views/cron_log_report_template.xml',
        'views/report.xml',
        'views/cron_mail_template.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'application': True,
    'auto_install': False,
}
