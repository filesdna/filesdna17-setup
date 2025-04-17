{
    'name': 'Sign Employee',
    'author': "Khalil Hamwi",
    'summary': 'Sign Employee',
    'application': True,
    'depends': ['hr', 'stock'],
    'data': [
        'views/sign_employee.xml',
        'views/stock_picking_inherit.xml',
        'views/account_move_inherit.xml',

    ],
}
