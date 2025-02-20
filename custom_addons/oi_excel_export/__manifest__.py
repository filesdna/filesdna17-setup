# -*- coding: utf-8 -*-
{
'name': 'Dynamic Excel Generation',
'summary': 'Easy create Excel report from Python code, Dynamic Excel Report, Global XLS '
           '''Report, Export Excel, Export XLS Data, 
'''
           'Excel Custom Template, XLS Custom Template, Excel Export, Excel Output, XLS '
           '''Export, Export XLS, XLSX Export, Export Special Fields Odoo
'''
           '    ',
'description': '''
        Easy create Excel report from Python code
    ''',
'author': 'Openinside',
'license': 'OPL-1',
'website': 'https://www.open-inside.com',
'price': 81.0,
'currency': 'USD',
'category': 'Extra Tools',
'version': '17.0.1.3.21',
'depends': ['base', 'web', 'oi_action_file', 'base_import'],
'data': ['security/ir.model.access.csv',
          'security/ir_rule.xml',
          'report/templates.xml',
          'report/report.xml'],
'demo': [],
'external_dependencies': {'python': ['xlsxwriter', 'openpyxl']},
'odoo-apps': True,
'auto_install': True,
'images': ['static/description/cover.gif'],
'application': False
}