import odoo
from odoo.http import request
from odoo.http import Session
from odoo.modules.registry import Registry

def authenticate_with_faceid(self, dbname, user_id):
    registry = Registry(dbname)
    user = request.env['res.users'].sudo().search([('id', '=', user_id)], limit=1)
    
    self.uid = None
    self.pre_login = user.login
    self.pre_uid = user.id

    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, user.id, {})

        # if 2FA is disabled we finalize immediately
        user = env['res.users'].browse(user.id)
        if not user._mfa_url():
            self.finalize(env)

    if request and request.session is self and request.db == dbname:
        # Like update_env(user=request.session.uid) but works when uid is None
        request.env = odoo.api.Environment(request.env.cr, self.uid, self.context)
        request.update_context(**self.context)

    return user.id

Session.authenticate_with_faceid = authenticate_with_faceid