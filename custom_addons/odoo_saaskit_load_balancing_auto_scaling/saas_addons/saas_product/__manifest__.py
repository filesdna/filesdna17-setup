{
    'name': 'SaaS-Master: Product/pricing on Website',
    "version": "1.29",
    'depends': ['website', 'website_sale', 'mail', "saas_base"],
    'license': 'OPL-1',
    "summary": "To view the saas products",
    'website': 'http://www.pragtech.co.in',
    "author": "Pragmatic Techsoft Pvt. Ltd.",
    "category": "SaaS",
    "description": """
    Performs some saas product functions
""",
    'data': [
        # 'data/mail_template.xml',
        'views/website_saas_menu.xml',
        'views/user_notification_template.xml',
        'views/saas_product_template.xml',
        'views/saas_tenant_details.xml',
        'views/saas_dbs_template.xml',
        'views/res_config_view.xml',
        # "file.sql",
    ],
    'assets': {
        'web.assets_frontend': [
            '/saas_product/static/src/js/manage_database.js',
            '/saas_product/static/src/js/product_template.js',
            '/saas_product/static/src/css/appointment.css',
            '/saas_product/static/src/select2-4.1.0-rc.0/dist/css/select2.min.css',
            '/saas_product/static/src/select2-4.1.0-rc.0/dist/js/select2.min.js',
        ],
    },
    'application': 'True',
    'post_load': "unarchive_users",  # monkey patch
}
