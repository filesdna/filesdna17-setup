# -*- coding: utf-8 -*-
#################################################################################
# Author      : CFIS (<https://www.cfis.store/>)
# Copyright(c): 2017-Present CFIS.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://www.cfis.store/>
#################################################################################

{
    "name": "Face Id Authentication | Login Face Recognition | Login Face Authentication",
    "summary": "This module allows the odoo users to login using Face Recognition. This functionality works in conjunction with User Employees Photograph while Login.",
    "version": "17.1",
    "description": """
        This module allows the odoo users to login using Face Recognition. 
        This functionality works in conjunction with User Employees Photograph while Login.
        Face Id Authentication.
        Login Face Recognition.
        Login Face Authentication.
    """,    
    "author": "CFIS",
    "maintainer": "CFIS",
    "license" :  "Other proprietary",
    "website": "https://www.cfis.store",
    "images": ["images/faceid_authentication.png"],
    "category": "Employees",
    "depends": [
        "base",
        "web",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/res_users_views.xml",
        "views/webclient_templates.xml",
        "views/res_config_settings.xml",
    ],
    "assets": {
        "web.assets_backend": [   
            # https://cdn.jsdelivr.net/npm/@vladmandic/human/dist/human.js
            "/faceid_authentication/static/src/lib/source/human.js", 
            "/faceid_authentication/static/src/css/style.css",

            "/faceid_authentication/static/src/js/image_users_webcam_dialog.js",
            "/faceid_authentication/static/src/js/image_users_webcam_dialog.xml",
            "/faceid_authentication/static/src/js/image_webcam.js",
            "/faceid_authentication/static/src/js/image_webcam.xml",
            "/faceid_authentication/static/src/js/field_one2many_descriptor.js",
            # "/faceid_authentication/static/src/js/*.*",
        ],
        'web.assets_frontend': [
            # https://cdn.jsdelivr.net/npm/@vladmandic/human/dist/human.js
            "/faceid_authentication/static/src/lib/source/human.js", 
            "/faceid_authentication/static/src/css/style.css",

            "/faceid_authentication/static/src/js/login_button.js",
            "/faceid_authentication/static/src/js/faceid_recognition_dialog.js",
            "/faceid_authentication/static/src/js/faceid_recognition_dialog.xml",
            "/faceid_authentication/static/src/xml/faceid_dialog.xml"
        ],
    },
    "installable": True,
    "application": True,
    "price"                :  120,
    "currency"             :  "EUR",
}
