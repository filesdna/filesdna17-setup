# -*- coding: utf-8 -*-
{
    'name': "openerp_dashboard",

    'summary': """Waste collection schedule module
    """,

    'description': """
        THis module is used for create weekly schedule for waste collection
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '17.0.0.2',

    # any module necessary for this one to work correctly
    'depends': ['base','web','openerp_saas_tenant'],

    # always loaded
    'data': [
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            "openerp_dashboard/static/src/xml/dashboard.xml",
            "openerp_dashboard/static/src/js/dashboard.js",
            "https://www.gstatic.com/charts/loader.js",
        ],
        # 'web.assets_qweb': [
        #     'pragtech_flt_schedule/static/src/xml/*.xml',
        # ],
    },
    # only loaded in demonstration mode
    # 'demo': [
    # ],
}
