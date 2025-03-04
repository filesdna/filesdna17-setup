# -*- coding: utf-8 -*-
{
    'name': "Multi Folders DMS",
    'summary': "Module to manage multiple upload folders in the Document Management System.",
    'description': """
    This module allows users to upload and manage documents 
    across multiple folders within 
    the Document Management System (DMS).
    """,
    'author': "Borderless Security FZCO",
    'website': "https://www.borderlesssecurity.com",
    'category': 'Documents',
    'version': '0.1.0',
    'depends': ['base', 'dms'],  
    'data': [
        'security/ir.model.access.csv',  
        'views/multi_folder_views.xml', 
    ],
   
}
