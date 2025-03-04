# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Pragmatic Techsoft.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    "name": "SaaS-Master:Ideal Connection Database",
    "version": "17.0.0.0",
    "depends": ["saas_base"],
    "author": "Pragmatic Techsoft Pvt. Ltd.",
    "category": "SaaS",
    "summary": "SaaS Base module",
    'license': 'OPL-1',
    "description": """
    Performs closing ideal postgres tenant connections.
""",
    'website': 'http://www.pragtech.co.in',
    'init_xml': [],
    'data': [
        'data/db_close_cron.xml',
    ],
    'demo_xml': [],
    'installable': True,
    'active': True,
}
