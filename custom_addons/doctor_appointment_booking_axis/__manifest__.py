# -*- coding: utf-8 -*-
{
    'name': "Doctor Appointment Booking in odoo, Clinic Website Appointment Booking in Odoo, Patient registration online",
    'summary': "Doctor Appointment Booking in odoo, Doctor Appointment Booking, Patient Appointment Booking, Clinic appointment, Dental appointment, Hospital Booking, Dental online booking, Hospital patient Booking system, hospital appointment slot booking, book appointment calendar booking consultant booking Patient registration online",
    'description': """
       Doctor Appointment Booking in odoo 17,16,15,14, 13, 12, Doctor Appointment Booking, Patient Appointment Booking, Clinic, Dental, Hospital Booking, Doctor calendar booking slot """,
    'category': 'website',
    'version': '17.0.0.0.2',
    # any module necessary for this one to work correctly
    'depends': ['base','calendar','account','crm','contacts',
                'website','website_sale', 'hr'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/website_calendar_data.xml',
	    'views/res_config_view.xml',
        'views/portal_templates_view.xml',
        'views/portal_appointment_templates.xml',
        'views/appointment_views.xml',
        'views/employee_inherit_view.xml',
        'views/menu_dashboard_view.xml',
        'views/website.xml',
        'views/website_view.xml',
        'views/appointment_source_views.xml',
        'views/appointee_views.xml',
        'views/appointment_group_views.xml',
        'views/appointment_timeslot_views.xml',
        'views/calendar_appointment_views.xml',
    ],

    'assets': {
        'web._assets_primary_variables': [
            '/doctor_appointment_booking_axis/static/src/css/custom_style.css',
        ],
        'web.assets_backend': [
            '/doctor_appointment_booking_axis/static/src/xml/**/*',
            '/doctor_appointment_booking_axis/static/src/js/appointment_dashboard.js',
            '/doctor_appointment_booking_axis/static/src/js/jquery.dataTables.min.js',
            '/doctor_appointment_booking_axis/static/src/js/datatables.min.js',
            '/doctor_appointment_booking_axis/static/src/js/dataTables.buttons.min.js',


            '/doctor_appointment_booking_axis/static/src/js/Chart.js',
            '/doctor_appointment_booking_axis/static/src/css/nv.d3.css',
            '/doctor_appointment_booking_axis/static/src/scss/style.scss',

        ],
        'web.assets_frontend': [
            '/doctor_appointment_booking_axis/static/src/css/custom_style.css',
            '/doctor_appointment_booking_axis/static/src/js/custom_step_wizard.js',
            '/doctor_appointment_booking_axis/static/src/js/custom.js',

        ],

    },


    'price': 199.00,
    'currency': 'USD',
    'support': 'business@axistechnolabs.com',
    'author': 'Axis Technolabs',
    'website': 'https://www.axistechnolabs.com',
    'installable': True,
    'license': 'OPL-1',
    'images': ['static/description/doctor_appointment.gif','static/description/images/banner.png'],

}
