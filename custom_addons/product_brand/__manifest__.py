# -*- coding: utf-8 -*-
{
    'name': "Product Brand",

    'summary': "Short (1 phrase/line) summary of the module's purpose",


    'author': "Borderless Security",
    'website': "https://www.borderlesssecurity.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['stock','base'],

    # always loaded
    'data': [
        'security/record_rules.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/product_templates.xml',
    ],
  
}

