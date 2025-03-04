{
    'name': 'SaaS-Tenant:',
    'version': '0.2',
    'category': 'SaaS',
    'description': """Openerp SAAS Tenant Restriction Module """,
    "summary": "Tenant restriction",
    'website': 'http://www.pragtech.co.in',
    'author': 'Pragmatic TechSoft Pvt. Ltd.',
    'license': 'OPL-1',
    'depends': ['openerp_saas_tenant','web_editor'],
    'data': [
        'security/saas_service_security.xml',
        'security/ir.model.access.csv',
        'views/template.xml',
        # 'views/users_view.xml',
        # 'vies/account_bank_view.xml',
    ],
    'assets': {
        'web.assets_backend': ["/openerp_saas_tenant_extension/static/src/css/im_chat.css"
                               ],
    },
    'qweb': [
        # 'static/src/xml/base.xml',
    ],

    'installable': True,
    'active': True,
}
