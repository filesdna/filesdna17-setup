{
    "name": "SaaS-Master:Billing Type Extension",
    "version": "0.29",
    "depends": ['base', 'saas_product', 'saas_recurring'],
    "author": "Pragmatic Techsoft Pvt. Ltd.",
    "category": "SaaS",
    "summary": "SaaS Billing type extension module",
    'license': 'OPL-1',
    "description": """
    Performs some basic functions to setup billing types for saas functionalities
""",
    'website': 'http://www.pragtech.co.in',
    'init_xml': [],
    'data': [
        'views/saas_product_template_inherit.xml',
        'views/res_config_inherit.xml',
        'views/sale_order_view.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            '/billing_type_extension/static/src/js/product_template.js',
        ],
    },
    'installable': True,
    'active': True,
}
