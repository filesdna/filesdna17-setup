{
    "name": "Brokerage",
    "summary": "Brokerage Module",
    "version": "17.0.0.1",
    # 'category': 'Uncategorized',
    "description": """
		Borderless Security Addons
    """,
    'images': [
        'static/description/cover.png'
    ],
    "installable": True,
    "depends": [
        'account'
    ],
    "data": [
        "security/ir.model.access.csv",
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
        'views/broker.xml',
    ]
}
