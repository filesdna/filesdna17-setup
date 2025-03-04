# -*- coding: utf-8 -*-
{
    'name': "DMS DashBoard",

    'summary': "DMS Dashboard",

    'description': """
        DMS Dashboard
    """,

    'author': "Borderless Security",
    'website': "https://www.borderlesssecurity.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'dms',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','dms'],

    # always loaded
    'data': [
    ],
    'assets': {
        'web.assets_backend': [
            'dms_dashboard/static/src/js/DmsDashBoard.js',
            'dms_dashboard/static/src/js/DmsDashBoard.xml'
        ],
    },
}

