# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Indian - Accounting',
    'website': 'https://www.filesdna.com/documentation/17.0/applications/finance/fiscal_localizations/india.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['in'],
    'version': '2.0',
    'description': """
Indian Accounting: Chart of Account.
====================================

Indian accounting chart and localization.

Odoo allows to manage Indian Accounting by providing Two Formats Of Chart of Accounts i.e Indian Chart Of Accounts - Standard and Indian Chart Of Accounts - Schedule VI.

Note: The Schedule VI has been revised by MCA and is applicable for all Balance Sheet made after
31st March, 2011. The Format has done away with earlier two options of format of Balance
Sheet, now only Vertical format has been permitted Which is Supported By Odoo.
  """,
    'category': 'Accounting/Localizations/Account Charts',
    'depends': [
        'account_tax_python',
        'base_vat',
    ],
    'data': [
        'security/l10n_in_security.xml',
        'security/ir.model.access.csv',
        'data/account_tax_report_tcs_data.xml',
        'data/account_tax_report_tds_data.xml',
        'data/account.account.tag.csv',
        'data/l10n_in_chart_data.xml',
        'data/l10n_in.port.code.csv',
        'data/res_country_state_data.xml',
        'data/uom_data.xml',
        'views/account_invoice_views.xml',
        'views/account_journal_views.xml',
        'views/res_config_settings_views.xml',
        'views/product_template_view.xml',
        'views/port_code_views.xml',
        'views/res_company_views.xml',
        'views/report_invoice.xml',
        'views/res_country_state_view.xml',
        'views/res_partner_views.xml',
        'views/account_tax_views.xml',
        'views/uom_uom_views.xml',
        'report/audit_trail_report_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
        'demo/product_demo.xml',
    ],
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'l10n_in/static/src/components/**/*',
        ],
    },
}
