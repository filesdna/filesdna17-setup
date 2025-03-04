from . import models

import base64
from odoo.tools import file_open

def _setup_module(env):
    bot_user = env['res.users'].browse(1)
    if bot_user.name == 'OdooBot':
        bot_user.write({'name': 'FilesdnaBot'})

    welcom_msg = env['mail.message'].search([('model','=','discuss.channel'),('subject','=','Welcome to Odoo!')])
    if welcom_msg:
        welcom_msg.write({'subject': 'Welcome to Filesdna!'})

    if env.ref('base.main_company', False):
        with file_open('branding_filesdna/static/src/img/favicon.ico', 'rb') as file:
            env.ref('base.main_company').write({'favicon': base64.b64encode(file.read())})
        with file_open('branding_filesdna/static/src/img/res_company_logo.png', 'rb') as file:
            env.ref('base.main_company').write({'appbar_image': base64.b64encode(file.read())})


def _uninstall_cleanup(env):
    env['res.config.settings']._reset_theme_color_assets()
    env['res.config.settings']._reset_light_color_assets()
    env['res.config.settings']._reset_dark_color_assets()