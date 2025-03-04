{
    'name': 'Sale Order Line Image',
    'version': '1.0',
    'summary': 'Add product image to sale order lines',
    'depends': ['base','sale','project','purchase','account','sale_stock','stock'],
    'data': [
        'views/views.xml',
        'views/stock_views.xml',
        'report/sale_order_report.xml',
        'report/report_stockpicking.xml'
    ],
    'installable': True,
    'application': False,
}
