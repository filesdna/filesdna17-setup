# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################
from . import models
from . import controllers
from . import tool


def pre_init_check(cr):
    from odoo.service import common
    from odoo.exceptions import UserError
    version_info = common.exp_version()
    server_serie = version_info.get('server_serie')
    if not 16.4 < float(server_serie) <= 17.0:
        raise UserError(f'Module support Odoo series 17.0 but found {server_serie}.')
    return True
