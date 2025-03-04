# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Branding Filesdna',
    'version' : '17.0.0.1',
    'summary': """ 

    """,
    'sequence': 10,
    'description': """
    """,
    'category': 'Extra Tools',
    'author': 'Filesdna',
    'depends': ['base','account','web','portal','web_editor'],
    'data': [
        'security/groups.xml',
        'views/res_users.xml',
        'views/templates.xml',
        'views/web_login.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            ('prepend', 'branding_filesdna/static/src/scss/colors.scss'),
            ('before', 'branding_filesdna/static/src/scss/colors.scss', 'branding_filesdna/static/src/scss/colors_light.scss'),
            ('branding_filesdna/static/src/scss/variables.scss'),
            ('after','web/static/src/scss/primary_variables.scss','branding_filesdna/static/src/scss/colors.scss'),
            ('after', 'web/static/src/scss/primary_variables.scss', 'branding_filesdna/static/src/scss/variables.scss'),
        ],
        'web.assets_web_dark': [
            ('after', 'branding_filesdna/static/src/scss/colors.scss', 'branding_filesdna/static/src/scss/colors_dark.scss' ),
            ('after', 'branding_filesdna/static/src/scss/variables.scss', 'branding_filesdna/static/src/scss/variables.dark.scss',),
        ],
        'web.assets_backend': [
            ('replace', 'web/static/src/webclient/navbar/navbar.variables.scss', 'branding_filesdna/static/src/webclient/navbar/navbar.scss'),
            ('after', 'web/static/src/webclient/webclient.js', 'branding_filesdna/static/src/webclient/webclient.js',),
            # ('after','web/static/src/webclient/webclient.xml', 'branding_filesdna/static/src/webclient/webclient.xml',) Found this line in appsbar module, but file not found.
            ('after', 'web/static/src/webclient/webclient.js', 'branding_filesdna/static/src/webclient/menus/app_menu_service.js',),
            ('after', 'web/static/src/webclient/webclient.js', 'branding_filesdna/static/src/webclient/appsbar/appsbar.js',),
            'branding_filesdna/static/src/webclient/webclient.scss',
            'branding_filesdna/static/src/webclient/appsbar/appsbar.xml',
            # 'branding_filesdna/static/src/webclient/appsbar/appsbar.scss', Duplicated below so commented out.
            # 'branding_filesdna/static/src/webclient/navbar.xml', Unable to locate the file so commented out.
            'branding_filesdna/static/src/webclient/**/*.xml',
            'branding_filesdna/static/src/webclient/**/*.scss',
            'branding_filesdna/static/src/webclient/**/*.js',
            # 'branding_filesdna/static/src/views/**/*.scss', Only one file exists forms.scss. Already loading above so commented out.
            'branding_filesdna/static/src/scss/side_menu.scss',
            'branding_filesdna/static/src/scss/mixins.scss',
        ],
        'web._assets_backend_helpers': [
            'branding_filesdna/static/src/scss/mixins.scss',
        ],
    },
    'images': [
        'static/description/icon.png',
    ],
    'installable': True,
    'application': True,

    'license': 'LGPL-3',
    'post_init_hook': '_setup_module',
    'uninstall_hook': '_uninstall_cleanup',
}
