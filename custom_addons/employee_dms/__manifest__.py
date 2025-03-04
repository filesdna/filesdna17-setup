# -*- coding: utf-8 -*-
{
    'name': "Employee DMS",

    'summary': "This module will allow the hr officers to upload all the related documents for employees in their profiles",

    'description': """
        A section to upload the employees files in their profile
    """,

    'author': "Borderless Security",
    'website': "https://www.borderlesssecurity.com",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['base','hr','dms'],

    'data': [
        'views/employee_views_dms.xml',
    ],
   
}

