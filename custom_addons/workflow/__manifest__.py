{
    'name': 'Workflow',
    'version': '1.0',
    'summary': 'Integrate React.js with Odoo',
    'description': 'Serve React.js frontend within Odoo and provide APIs.',
    'author': 'Your Name',
    'category': 'Tools',
    'depends': ['base','mail'],
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
        'web.assets_common': [
            # React and ReactDOM from CDN
            'https://unpkg.com/react@18/umd/react.production.min.js',
            'https://unpkg.com/react-dom@18/umd/react-dom.production.min.js',
        ]
    },
}