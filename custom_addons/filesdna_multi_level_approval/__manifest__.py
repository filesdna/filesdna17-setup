{
    "name": "Filesdna Approval",
    "version": "17.0.1.0.0",
    "category": "Approvals",
    "summary": """
    Create and validate approval requests.
    Each request can be approved by many levels of different managers
    """,
    # "live_test_url": "https://demo16.domiup.com",
    # "author": "Domiup (domiup.contact@gmail.com)",
    # "price": 70,
    # "currency": "USD",
    "license": "OPL-1",
    # "support": "domiup.contact@gmail.com",
    # "website": "https://youtu.be/PJ7lTUn-qes",
    "depends": ["mail", "product"],
    "data": [
        "data/ir_sequence_data.xml",
        # "data/mail_template_data.xml",
        "security/security.xml",
        "security/ir.model.access.csv",
        # wizard
        "wizard/cancel_approval_views.xml",
        "wizard/change_approver_views.xml",
        "wizard/request_approval_views.xml",
        "wizard/rework_approval_views.xml",
        "wizard/test_approval_views.xml",
        "wizard/refused_reason_views.xml",
        "views/multi_approval_type_views.xml",
        "views/multi_approval_views.xml",
        # Add actions after all views.
        "views/actions.xml",
        # Add menu after actions.
        "views/menu.xml",
        "views/multi_approval_type_views_full.xml",
        "views/multi_approval_views_full.xml",
    ],
    "images": ["static/description/banner.jpg"],
    "test": [],
    "demo": [],
    "installable": True,
    "application": True,
}
