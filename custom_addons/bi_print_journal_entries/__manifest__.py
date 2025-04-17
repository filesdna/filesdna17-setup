# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Print Journal Entries Report in Odoo',
    'version': '17.0.0.0',
    'category': 'Account',
    'license': 'OPL-1',
    'summary': 'Allow to print pdf report of Journal Entries.',
    'description': """
    Allow to print pdf report of Journal Entries.
    journal entry
    print journal entry 
    journal entries
    print journal entry reports
    account journal entry reports
    journal reports
    account entry reports

    
""",
    'price': 000,
    'currency': 'EUR',
    'author': 'BrowseInfo',
    'website': 'https://www.browseinfo.com',
    'depends': ['base', 'account', 'sale_management', 'purchase'],
    'data': [
        "security/ir.model.access.csv",
        'views/account_move_inherit.xml',
        'report/report_journal_entries.xml',
        'report/report_journal_entries_view.xml',
        'report/invoice_profit_report_template.xml',
        'report/purchase_order_report.xml',
        'report/product_report.xml',
        'report/customer_report.xml',
        'report/customer_product_report.xml',
        'report/reference_report.xml',
        'wizard/invoice_profit_report.xml',
        'wizard/purchase_report.xml',

    ],
    'installable': True,
    'auto_install': False,
    'live_test_url': 'https://youtu.be/qehLT4WOWPs',
    "images": ["static/description/Banner.gif"],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
