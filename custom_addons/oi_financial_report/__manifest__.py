# -*- coding: utf-8 -*-
{
'name': 'Dynamic Financial Report',
'summary': '''
'''
           '            Dynamic Financial Report, Trial Balance, Profit and Loss, '
           'Dynamic Report, Balance Sheet, Profit & Loss, Income Statement, Balance '
           '''Sheet, P&L
'''
           '        ',
'description': '''
        Dynamic & configurable Financial Report
    ''',
'author': 'Openinside',
'website': 'https://www.open-inside.com',
'price': 400.0,
'currency': 'USD',
'license': 'OPL-1',
'category': 'Accounting',
'version': '17.0.2.4.2',
'depends': ['base', 'account', 'oi_excel_export', 'oi_pdf_viewer'],
'data': ['security/ir.model.access.csv',
          'views/filter.xml',
          'views/dataTemplate.xml',
          'views/data.xml',
          'views/report_source.xml',
          'views/report_template.xml',
          'views/report.xml',
          'views/oi_fin_template_source.xml',
          'views/oi_fin_aged_partner_template.xml',
          'views/oi_fin_aged_partner_wizard.xml',
          'report/report.xml',
          'report/templates.xml',
          'views/action.xml',
          'views/menu.xml',
          'data/config_data.xml',
          'data/account_report_source.xml',
          'data/balance_sheet.xml',
          'data/general_ledger.xml',
          'data/profit_and_Loss.xml',
          'data/trial_balance.xml',
          'data/cash_flow_statement.xml',
          'views/oi_fin_dimension.xml',
          'data/menu.xml',
          'data/function.sql',
          ],
'images': ['static/description/cover.png'],
'odoo-apps': True,
'application': False
}