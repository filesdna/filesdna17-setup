{
    'name': 'SaaS-Master/SaaS-Tenant:Domain Masking Website',
    'version': '0.4',
    'category': 'SaaS',
    'author': 'Pragmatic TechSoft Pvt Ltd.',
    'website': 'http://www.pragtech.co.in',
    'summary': 'SaaS-Master/SaaS-Tenant:Domain Masking software as a service odoo saas pragmatic saas Saaskit saas script software odoo saas odoo saaskit odoo saaskit software pragmatic saaskit saas pack cloud Odoo SaaS Kit odoo_saas_kit saas business',
    'depends': ['odoo_pragtech_domain_masking'],
    'description': """
This module helps to add a separate domain name to the tenant database url from website. If tenant has their own domain registered and wish to access Odoo tenant database using their own domain, then this module helps to do the same. Technically this is called domain masking.
""",
    'data': [
        'views/saas_dbs_template_extended_view.xml',
        'views/res_config_view.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            '/odoo_pragtech_domain_masking_website/static/src/css/domain_form.css',
            '/odoo_pragtech_domain_masking_website/static/src/js/domain_form.js'
        ],
    },
    'images': ['static/description/animated-domain-masking.gif'],
    'license': 'OPL-1',
    'application': True,
    'auto_install': False,
    'installable': True,
}
