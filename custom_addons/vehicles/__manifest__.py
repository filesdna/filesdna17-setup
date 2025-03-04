{
    'name': 'Vehicles',
    "version": "1.2",
    "category": "Vehicles Management",
    'author': "Borderless Security",    "summary": """Vehicles For Filesdna""",
    'application': True,
    'depends': ['hr'],
    'data': [
        "security/ir.model.access.csv",
        "views/base_menu.xml",
        "views/vehicles.xml",
        "views/vehicles_type.xml",
        "views/hr_employee_inherit.xml",
    ],
}
