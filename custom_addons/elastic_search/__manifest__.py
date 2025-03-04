# -*- coding: utf-8 -*-
{
    'name': "Elastic Document Management",

    'summary': "Manage documents and index them in Elasticsearch",

    'description': """
                Manage documents and index them in Elasticsearch
    """,

    'author': "Borderlessecurity",
    'website': "https://www.borderlesssecurity.com",

    'category': 'Document Management',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','dms'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/elastic_search.xml',
        'views/views.xml',
    ],
    # "assets": {
    #     "web.assets_backend": [
    #         "/elastic_search/static/src/js/tag_input.js",
    #     ],
    # }
}

