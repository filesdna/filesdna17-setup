
###############################################################################
{
    'name': "Hide Price, Add To Cart And Quantity Button In Website",
    'version': '17.0.2.0.0',
    'category': 'Website',
    'summary': """Hide Price, Add To Cart and Quantity button for guest
     users""",
    'description': """Login user can see Price of the Product in shop page and
     Price of the Product, Quantity and Add To Cart button. But these 
     features will be hidden for guest users.""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['website_sale'],
    'data': [
        'views/product_templates.xml',
        'views/shop_templates.xml',
        'views/res_config_settings_views.xml'
    ],
    'images': ['static/description/banner.jpg'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
