# -*- coding: utf-8 -*-
{
    'name': "DMS Editor",

    "summary": """Document Management System for FilesDNA""",
    "category": "Document Management",
    'license': 'LGPL-3',
    'author': "Yaseen - Borderless Security",
    'website': "https://www.borderlesssecurity.com/",
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','dms'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        "views/delegation.xml",
        "views/signature.xml",
        "views/sign_requests.xml",
        'views/edit.xml',
        'data/ir_cron_data.xml',

    ],

    "assets": {
        "web.assets_frontend": [
            "/dms_editor/static/src/js/token_local_storage.js",
        ],
        "web.assets_backend": [
            # "/dms_editor/static/src/js/config-v2.js",
            # "/dms_editor/static/src/js/sign_button.js",
            "/dms_editor/static/src/css/sign_button.css"
           
          
        ],
     
    },  

}

