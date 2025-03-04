# -*- coding: utf-8 -*-
{
    'name': "dms_face_recogintion",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
        Long description of module's purpose
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
        # 'views/views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # 'dms_face_recogintion/static/src/js/face_recognition.js',
        ],
    },
}

