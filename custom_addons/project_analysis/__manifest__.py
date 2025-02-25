{
    'name': 'Project Analysis',
    'version': '17.0.0.1',
    'summary': """ 
        Advanced project financial analysis, cost tracking, and labor cost computation.
    """,
    'description': """
        The **Project Analysis** module enhances project management by integrating financial and HR functionalities.
        This module allows businesses to track project-related expenses, labor costs, sales, and purchases 
        while maintaining real-time insights into profitability.

        **Key Features:**
        - Compute total working hours and overtime for employees based on attendance.
        - Link employee contracts to projects for automated salary calculations.
        - Track and analyze project expenses, purchases, and revenue.
        - Display detailed financial overviews, including sales, expenses, labor costs, and profit/loss.
        - Seamless integration with HR Attendance, Contracts, Payroll, and Accounting.
        - Enhance project cost estimation for better financial planning.
    """,
    'category': 'Extra Tools',
    'author': 'Borderless Security',
    'depends': ['base',
                'sale_management',
                'crm',
                'sale_crm',
                'account',
                'purchase',
                'project',
                'hr',  # Core HR module
                'hr_attendance',  # Attendance tracking
                'hr_contract',  # Employee contracts
                'hr_expense',  # Expense management
                'payroll',  # Payroll for salary computations
                ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/crm_lead_views.xml',
        # 'data/hr_payroll_groups.xml',
        'views/hr_attendance_inherit.xml',
        'views/hr_expense_view.xml',
        'views/hr_contract_views.xml',
        'views/project_project_views.xml',
        'views/purchase_order_form.xml',
        'views/hr_payslip_views.xml',
        # 'security/hr_payroll_security.xml',
        'wizard/sale_order_decline_wizard.xml',

    ],

    'assets': {
        'web.assets_backend': [
            'project_analysis/static/src/css/custom_styles.css',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',

}
