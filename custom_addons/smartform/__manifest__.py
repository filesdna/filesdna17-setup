{
    'name': 'Smartform',
    'version': '1.0',
    'summary': 'Integrate React.js with Odoo',
    'description': 'Serve React.js frontend within Odoo and provide APIs.',
    'author': 'Your Name',
    'category': 'Tools',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/react_page_views.xml',
        'views/react_menu.xml',
    ],
    'demo': [
      
    ],
   'assets': {
        'web.assets_backend': [
            # 'react_module/static/src/js/react_form_controller.js',
        ],

        "web.assets_frontend": [
            "/dms_editor/static/src/css/*.*",
          
        ],
    },
}