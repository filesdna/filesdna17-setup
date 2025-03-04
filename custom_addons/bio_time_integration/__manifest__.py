# -*- coding: utf-8 -*-
{
    'name': "Bio Time Integration",



    'author': "Mahdi babiker",

  
    'category': 'Uncategorized',
    'version': '0.1',
    'license': 'LGPL-3',
    # any module necessary for this one to work correctly
    'depends': ['base','hr','hr_attendance'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
}

