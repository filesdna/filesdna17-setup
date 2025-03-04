from odoo.api import Environment
from odoo.http import request
from odoo import http
from odoo import api, fields, models
import json
import odoo
from odoo.tools import config
import logging
_logger = logging.getLogger(__name__)

ADMINUSER_ID = 2

from odoo.addons.web.controllers.main import Database

DBNAME_PATTERN = '^[a-zA-Z0-9][a-zA-Z0-9_.-]+$'

from odoo.addons.web.controllers.home import Home
from odoo.addons.web.controllers import main
import re

import werkzeug
import werkzeug.exceptions
import werkzeug.utils
import werkzeug.wrappers
import werkzeug.wsgi
from odoo.exceptions import AccessError, UserError, AccessDenied

    
class InheritHome(Home):
    @http.route()
    def web_login(self, redirect=None, **kw):
        res = super(InheritHome, self).web_login(redirect, **kw)
        expire = False
        try:
            expire = request.env['db.expire'].search([], limit=1)
            # print(expire)
        except Exception as e:
            print(e)
        # print('________________________+++++', expire)
        if expire and expire.db_expire == True:
            response = request.render('openerp_saas_tenant.login_locked', {})
            return response
        else:
            return res


class Database_Manager(http.Controller):

    @http.route('/web/check_manage_db', auth='public', website=True, csrf=False)
    def check_manage_db(self, **kw):
        request.session.logout(keep_db=True)
        try:
            uid = request.session.authenticate(config['db_name'] or 'saasmaster_v17', kw['user_id'], kw['user_pwd'])
            if uid:
                user = request.env['res.users'].sudo().browse(uid)
                if user.has_group("saas_base.manage_page"):
                    request.session['allow'] = True
                    # return http.local_redirect('/web/database/manager')
                    return request.redirect('/web/database/manager')
                else:
                    response = request.render('db_filter.manage_select_db',
                                              {"error": "You don't have access to this page"})
                    return response
            else:
                response = request.render('db_filter.manage_select_db', {"error": "Username or Password is wrong"})
                return response
        except Exception as e:
            response = request.render('db_filter.manage_select_db', {"error": str(e)})
            return response

    @http.route('/web/database/selector', type='http', auth="none")
    def selector(self, **kw):

        if 'allow' in request.session and request.session['allow'] is True:
            # request._cr = None
            request.env.cr.close()
            request.session['allow'] = False
            del request.session['allow']
            return Database._render_template(self, manage=False)
        else:
            response = request.render('db_filter.manage_select_db', {'error': ""})
            return response

    @http.route('/web/database/manager', type='http', auth="none")
    def manager(self, **kw):
        if 'allow' in request.session and request.session['allow'] is True:
            request.env.cr.close()
            request.session['allow'] = False
            del request.session['allow']
            return Database._render_template(self)
        else:
            response = request.render('db_filter.manage_select_db', {'error': ""})
            return response

def db_filter(dbs, host=None):
    
    # val = request.httprequest.headers.environ.get('HTTP_REFERER')
    # forwarded_host = request.httprequest.headers.environ.get('HTTP_X_FORWARDED_HOST')
    host_url = host or request.httprequest.host_url
    # _logger.info("host_urlllllllllllllllllllllllllllll ................{}".format(host_url)) 
    # _logger.info("vallllllllllllllllllllllll ................{}".format(val))
    # _logger.info("forwarded_hostttttttttttttttttttttttttttt ................{}".format(forwarded_host))
    httprequest = host or request.httprequest
    
    main_database = 'saasmaster_v17'
    databases = odoo.service.db.list_dbs(True)
    dbs = databases
    test_db = False
    
    try:
        from contextlib import closing
        chosen_template = odoo.tools.config['db_template']
        templates_list = tuple(set(['postgres', chosen_template]))
        db = odoo.sql_db.db_connect('postgres')
        with closing(db.cursor()) as cr:
            try:
                cr.execute(
                    "select datname from pg_database where datdba=(select usesysid from pg_user where usename=current_user) and not datistemplate and datallowconn and datname not in %s order by datname",
                    (templates_list,))
                dbs = [odoo.tools.ustr(name) for (name,) in cr.fetchall()]

            except Exception:
                import traceback
    except Exception as e:
        _logger.info("exceptionnnnnnnn ................{}".format(e))
        
    # _logger.info("DATABASE_VAR ................{}".format(DATABASE_VAR))    
    # if DATABASE_VAR < 1:
        # DATABASE_VAR += 1
    
    if host_url:
        dd,yy,zz = host_url.partition('.')
        tname = ''
        # _logger.info("yyyyyyyyyyyyy ................{}".format(dd))   
        if '//' in dd: 
            tname = dd.partition('//')[2]
            # _logger.info("////////////////////////////////// ................{}".format(tname))
        elif '.' in dd:
            tname = dd.partition('.')[2]
            # _logger.info("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx ................{}".format(tname))
        if tname in dbs:
            _logger.info("inside returnnnnnnnnn ................{}".format(tname))
            return [tname]
    # if forwarded_host:
    #     dd,yy,zz = forwarded_host.partition('.')
    #     _logger.info("yyyyyyyyyyyyy ................{}".format(dd))
    #     if dd in dbs:
    #         _logger.info("inside returnnnnnnnnn ................{}".format(dd))
    #         return [dd]    
    h= host
    # _logger.info("hostttttttt ................{}".format(h))
    if h:
        # h = httprequest.environ.get('HTTP_HOST').split(".")[0]
        
        d, xyz, r = h.partition('.')
        if d == main_database:
            # print("d"*88,d)
            d = main_database
        # print("d"*88,d,test_db)
        # print("2"*88,dbs)
        if d in dbs and test_db == False:
            # print("dbs"*88,dbs,d)
            # _logger.info("dbsssssssssssssss ................{}".format(dbs))
            # _logger.info("ddddddddddddddddd ................{}".format(d))
            # print("1"*88,list(d),type(d))
            return [d]
            r = odoo.tools.config['dbfilter'].replace('%h', h).replace('%d', d)
        elif h:
            # _logger.info("inside eliffffffffff ................")
            registry = odoo.registry(main_database)
            with closing(registry.cursor()) as cr:
                env = Environment(cr, ADMINUSER_ID, {})
                try:
                    db_list = env['tenant.database.list'].sudo().search([])
                    # print('0000000000000000000000000011111 {}'.format(db_list))
                    for name in db_list:
                        # print('00000000000000000000000000222222 {}'.format(name))
                        # m = httprequest.environ.get('HTTP_HOST')
                        m = main_database
                        try:
                            if name.domain_masking_fields:
                                # print('00000000000000000000000000 :  return 00 : {}'.format(m,))
                                for nnn in name.domain_masking_fields:
                                    # print('00000000000000000000000000 :  return 000 : {}'.format(nnn.client_domain,))
                                    if m == nnn.client_domain:
                                        # h = nnn.tenant_name
                                        h = name.name
                                        h = h.split(".")[0]
                                        d, xyz, r = h.partition('.')
                                        if d in dbs:
                                            # print('00000000000000000000000000 :  return 1 : {}'.format(d))
                                            return [d]
                                            r = odoo.tools.config['dbfilter'].replace('%h', h).replace('%d', d)
                                    # else:
                                    #     print('00000000000000000000000000 :  return 2 : {}'.format(d))
                                    #     d = main_database
                                    #     print('00000000000000000000000000 :  return 2 : {}'.format(d))
                                    #     return [d]
                                    #     r = odoo.tools.config['dbfilter'].replace('%h', h).replace('%d', d)
                            # else:
                            #     print('00000000000000000000000000 :  return 3 : {}'.format(d))
                            #     d = main_database
                            #     return [d]
                            #     r = odoo.tools.config['dbfilter'].replace('%h', h).replace('%d', d)
                        except Exception as e:
                            # print('00000000000000000000000000 :  return 4 : {}'.format(d))
                            return [main_database]
                    else:
                        # _logger.info("elseeeeeeeeeeeeeeee ................")
                        # print('00000000000000000000000000 :  return 5 : {}'.format(d))
                        d = main_database
                        return [d]
                        r = odoo.tools.config['dbfilter'].replace('%h', h).replace('%d', d)
                except Exception as e:
                    # print('00000000000000000000000000 :  return 6 : {}'.format(d))
                    return [main_database]
        else:
            # print('00000000000000000000000000 :  return 7 : {}'.format(d))
            return [main_database]
        if d == 'saasmaster_v17':
            return [d]
            r = odoo.tools.config['dbfilter'].replace('%h', h).replace('%d', d)
        if d == 'www':
            d = r.partition('.')[0]
            r = odoo.tools.config['dbfilter'].replace('%h', h).replace('%d', d)
            filter_dbs = [d]
            dbs = [i for i in dbs if i in filter_dbs]
        if not dbs:
            dbs = [main_database]
    if main_database in dbs:
        httprequest.environ['HTTP_HOST'] = httprequest.environ['HTTP_HOST']
    return dbs

# print('\n\n\n @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@http: {}  {} {}'.format(http, db_filter, http.db_filter))
http.db_filter = db_filter