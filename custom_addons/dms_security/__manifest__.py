# -*- coding: utf-8 -*-
{
    'name': "DMS Security",

    'summary': "This Module to add some security option to keep Files more secure",

    'description': """
                    This Module to add some security option to keep Files more secure
    """,

    'author': "Borderless Security",
    'website': "https://www.borderlesssecurity.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'dms',
    'version': '0.1',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base','dms'],

    # always loaded
    "data": [
        "security/security_groups.xml",
        "security/ir.model.access.csv",
        "views/dms_security.xml",
        "views/dms_file.xml",
        "views/res_users_nfc.xml",
        "views/dms_directory.xml",
        "wizard/authenticator.xml",
        "data/data.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'dms_security/static/src/js/dismiss.js',
            'dms_security/static/src/js/search_model.js',
            'dms_security/static/src/js/FilePermission.js',
            'dms_security/static/src/css/FilePermission.css',
            'dms_security/static/src/xml/FilePermission.xml',
            'dms_security/static/src/js/ActiveSecurity.js',
            'dms_security/static/src/xml/ActiveSecurity.xml',
        ],
    },
    
}

