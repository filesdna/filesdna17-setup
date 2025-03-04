# -*- coding: utf-8 -*-
############################################################################
{
    'name': 'Payroll Accounting',
    'version': '17.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'FilesDNA  HR Payroll, payroll, FilesDNA Payroll, FilesDNA Payroll, Payroll, FilesDNA Payslips, Employee Payroll, HR Payroll,FilesDNA, FilesDNA HR, FilesDNA hr,FilesDNA, Accounting,FilesDNA Apps',
    'description': """ This module helps you to manage payroll and 
     accounting.""",
    'test': ['../account/test/account_minimal_test.xml'],
    'author': 'Borderless Security',
    'company': 'Borderless Security',
    'maintainer': 'Borderless Security',
    'website': "https://www.openhrms.com",
    'depends': ['payroll', 'account'],
    'data': ['views/hr_contract_views.xml',
             'views/hr_payslip_run_views.xml',
             'views/hr_payslip_views.xml',
             'views/hr_salary_rule_views.xml', ],
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
