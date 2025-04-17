{
    'name': 'Attachment Socket',
    'version': '1.0',
    'summary': 'Module to manage authentication tokens for WebSocket connections',
    'description': 'This module provides functionality to manage authentication tokens and validate them for WebSocket connections.',
    'category': 'Tools',
    'author': 'Your Name',
    'depends': ['base', "filesdna_signup", 'dms'],
    'data': [
        'security/ir.model.access.csv',
        'views/auth_token_views.xml',
        # 'views/views.xml',
        'data/update_token.xml'
    ],
    'installable': True,
    'application': True,
}
