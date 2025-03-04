# -*- coding: utf-8 -*-
{
    'name': "Employee More Details V2",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "Mahdi Babiker",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','hr','hr_contract','payroll'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/hr_contract.xml',
        'views/hr_employee.xml',
        'views/hr_job_address.xml',
        'views/hr_payslip.xml',
        'views/hide_chat.xml',
        'views/server_action.xml',
        'views/hr_payslip_allotment_type.xml',
        'views/res_partner_bank.xml',
        'views/employee_education.xml',
        
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

