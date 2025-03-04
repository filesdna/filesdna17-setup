# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
{
    'name': "Law Management | Law Firm | Lawyer Firms Practice | Laws",
    'version': "1.4",
    'description': "Law Management",
    'summary': "Law Management",
    'category': 'Industry',
    'author': 'TechKhedut Inc.',
    'website': "https://techkhedut.com",
    'depends': ['contacts', 'crm', 'project','dms'],
    'data': [
        # data
        'data/sequence_views.xml',
        'data/default_data_views.xml',
        'data/law_practise_area_data_views.xml',
        'data/matter_category_data.xml',
        'data/case_matter_close_mail.xml',
        # 'data/directories.xml',
        # security
        'security/security.xml',
        'security/record_rules.xml',
        'security/ir.model.access.csv',
        # wizards
        'wizards/case_matter_create_views.xml',
        'wizards/sub_case_create.xml',
        # views
        'views/assets.xml',
        'views/dms_law_view.xml',
        'views/law_practise_area_views.xml',
        'views/law_court_views.xml',
        'views/case_victim_views.xml',
        'views/acts_articles_views.xml',
        'views/case_favor_views.xml',
        'views/matter_category_views.xml',
        'views/case_evidence_views.xml',
        'views/court_trial_views.xml',
        'views/case_matter_views.xml',
        'views/customer_views.xml',
        'views/case_witness_views.xml',
        'views/leads_views.xml',
        'views/matter_document_views.xml',
        'views/project_task_views.xml',
        'report/matter_report.xml',
        'views/case_document_type_view.xml',
        # menus
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tk_law_management/static/src/xml/template.xml',
            'tk_law_management/static/src/scss/style.scss',
            'tk_law_management/static/src/js/lib/apexcharts.js',
            'tk_law_management/static/src/js/dashboard/law_dashboard.js',
        ],
    },
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'OPL-1',
    'price': 49,
    'currency': 'EUR'
}
