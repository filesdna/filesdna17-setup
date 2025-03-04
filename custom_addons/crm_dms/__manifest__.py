# -*- coding: utf-8 -*-
{
    'name': "CRM DMS",

    'summary': "This Module to add A dms file that related to crm record for specific case",

  

    'author': "Borderless Security FZCO",
    'website': "https://www.borderlessscurity.com",


    'category': 'crm',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','crm','dms'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/dms_file.xml',
        'views/lead.xml',
    ],
  
}

