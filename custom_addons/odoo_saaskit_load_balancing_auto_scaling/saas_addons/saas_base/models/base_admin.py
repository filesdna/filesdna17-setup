import xmlrpc
from odoo import models, fields, api, _
import time
# from mx.DateTime import RelativeDateTime
# import mx.DateTime
from odoo.tools import config, get_lang
import logging
from contextlib import closing
from odoo.service import db
import odoo.addons.decimal_precision as dp
# from pragmatic_saas.saas_base.admin_user import ADMINUSER_ID
# from sass_base.admin_user import ADMINUSER_ID
from datetime import datetime as dt
import datetime
import odoo
from odoo.exceptions import UserError, ValidationError

ADMINUSER_ID = 2
_logger = logging.getLogger(__name__)

from odoo.http import request


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    def _handle_website_page_visit(self, website_page, visitor_sudo):
        """ Called on dispatch. This will create a website.visitor if the http request object
        is a tracked website page or a tracked view. Only on tracked elements to avoid having
        too much operations done on every page or other http requests.
        Note: The side effect is that the last_connection_datetime is updated ONLY on tracked elements."""
        url = ""
        if 'environ' in request.httprequest.__dict__ and 'HTTP_REFERER' in request.httprequest.__dict__['environ']:
            url = request.httprequest.__dict__['environ']['HTTP_REFERER']
        else:
            url = request.httprequest.url
        website_track_values = {
            'url': url,
            'visit_datetime': dt.now(),
        }
        if website_page:
            website_track_values['page_id'] = website_page.id
            domain = [('page_id', '=', website_page.id)]
        else:
            domain = [('url', '=', url)]
        visitor_sudo._add_tracking(domain, website_track_values)
        if visitor_sudo.lang_id.id != request.lang.id:
            visitor_sudo.write({'lang_id': request.lang.id})


class tenant_database_stage(models.Model):
    _name = "tenant.database.stage"
    _description = "Stage of case"
    _rec_name = 'name'
    _order = "sequence"

    def write(self, vals):
        if 'is_active' in vals:
            del vals['is_active']
        if 'is_grace' in vals:
            del vals['is_grace']
        if 'is_expired' in vals:
            del vals['is_expired']
        if 'is_purge' in vals:
            del vals['is_purge']
        if 'is_deactivated' in vals:
            del vals['is_deactivated']
        return super(tenant_database_stage, self).write(vals)

    name = fields.Char('Stage Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', help="Used to order stages. Lower is better.", default=1)
    fold = fields.Boolean('Folded in Kanban View',
                          help='This stage is folded in the kanban view when'
                               'there are no records in that stage to display.')
    is_active = fields.Boolean('Active', default=False)
    is_grace = fields.Boolean('In Grace Period', default=False)
    is_expired = fields.Boolean('Expired', default=False)
    is_deactivated = fields.Boolean('Deactivated', default=False)
    is_purge = fields.Boolean('Purge', default=False)


# tenant_database_stage()


class tenant_database_list(models.Model):
    _name = "tenant.database.list"
    _description = 'Tenant Database List'

    ingraceperiod = fields.Boolean(related="stage_id.is_grace", )
    inexpiredstate = fields.Boolean(related="stage_id.is_expired", )

    def on_change_tenant_db_info(self):
        # for record in self:
        ICPSudo = self.env['ir.config_parameter'].sudo()
        admin_login = ICPSudo.search([('key', '=', 'admin_login')]).value
        admin_pwd = ICPSudo.search([('key', '=', 'admin_pwd')]).value
        brand_website = ICPSudo.search([('key', '=', 'brand_website')])
        db_ids = [i.id for i in self.env["tenant.database.list"].search([])]
        for db in self.env["tenant.database.list"].browse(db_ids):
            try:
                registry = odoo.registry(db.name)
                with closing(registry.cursor()) as tenant_cr:
                    tenant_env = odoo.api.Environment(tenant_cr, ADMINUSER_ID, {})
                    ret = tenant_env['res.users'].browse(2).write(
                        {'password': admin_pwd, 'login': admin_login})
            except Exception as e:
                print(e)

    def increase_no_of_users_forcely(self):
        _logger.info('--------------------{}'.format(self))
        wizard_obj = self.env['increase.tenant.users.wizard'].sudo()
        res_id = wizard_obj.create({
            'default_no_of_users': self.no_of_users,
            'updated_no_of_users': self.no_of_users
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'increase.tenant.users.wizard',
            'res_id': int(res_id.id),
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {
                'wiz_id': self.id,
            },
        }


    def check_sequence_number(self, instance_name,sequence_no,old_instance_name):
        tenanat_object = request.env["tenant.database.list"].sudo().search(
        [('name', '=', str(instance_name))])
        if not tenanat_object:
            return instance_name,sequence_no
        else:

            instance_name = str(old_instance_name) + '_' + str(sequence_no)
            sequence_no += 1
            return self.check_sequence_number(instance_name,sequence_no,old_instance_name)


    def check_phone_number(self, instance_name,sequence_no,tenant_name,old_instance_name):
        self._cr.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
        db_names = self._cr.fetchall()
        db_name_set = map(lambda x: x[0], db_names)
        db_name_list = list(db_name_set)
        # sequence_ids = sequence_no
        for sequence in range(1, len(db_name_list)):
            if tenant_name in db_name_list:
                tenant_name = str(old_instance_name) + '_' + str(sequence_no)
                sequence_no += 1
                return self.check_phone_number(instance_name= instance_name,sequence_no=sequence_no,tenant_name = tenant_name,old_instance_name=old_instance_name)

            else:
                return tenant_name,sequence_no


    def check_sale_order(self,instance_name,sequence_no,tenant_name,old_instance_name):
        saleobject = self.env['sale.order'].search([('state', 'not in', ['draft', 'cancel'])])
        for order in saleobject:
            if order.instance_name == tenant_name:
                tenant_name = str(old_instance_name) + '_' + str(sequence_no)
                sequence_no += 1
                return self.check_sale_order(instance_name=instance_name,sequence_no = sequence_no,tenant_name = tenant_name,old_instance_name=old_instance_name)
        return tenant_name, sequence_no


    def write(self, vals):
        res = super(tenant_database_list, self).write(vals)
        for rec in self:
            try:
                if 'exp_date' in vals:
                    ICPSudo = self.env['ir.config_parameter'].sudo()
                    brand_website = ICPSudo.search([('key', '=', 'brand_website')]).value
                    dest_model = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(brand_website))
                    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(brand_website))
                    db_name = rec.name
                    admin_login = str(rec.super_user_login) or 'admin'
                    brand_pwd = rec.super_user_pwd or 'admin'
                    uid_dst = common.authenticate(db_name, admin_login, brand_pwd, {})
                    if not uid_dst:
                        uid_dst = common.authenticate(db_name, 'admin', 'admin', {})
                        brand_pwd = 'admin'

                    service_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'saas.service', 'search', [[]])
                    for service_id in service_ids:
                        dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'saas.service', 'write',
                                              [service_id,
                                               {
                                                   'expiry_date': vals['exp_date']
                                               }]
                                              )
            except Exception as err:
                raise ValidationError('Could not connect to Tenant Database! Please Contact Administrator!')
        return res

    def _make_invoice(self):
        agreement_order_obj = self.env['sale.recurring.orders.agreement.order']
        invoice_line_obj = self.env['account.move.line']
        invoice_obj = self.env['account.move']
        journal_obj = self.env['account.journal']
        today = time.strftime('%Y-%m-%d')
        move_id = None

        ## check agreement is created for this tenant
        agreement_order_id = agreement_order_obj.sudo().search(
            [('order_id', '=', self.sale_order_ref.id), ('agreement_id.active', '=', True)],
            limit=1)
        if agreement_order_id:
            res = journal_obj.search([('type', '=', 'sale')], limit=1)
            journal_id = res and res[0] or False
            account_id = self.sale_order_ref.partner_id.property_account_receivable_id.id
            # invoice_vals = {
            #     'name': self.sale_order_ref.name,
            #     'invoice_origin': self.sale_order_ref.name,
            #     'comment': 'SaaS Recurring Invoice',
            #     'date_invoice': today,
            #     'address_invoice_id':self.sale_order_ref.partner_invoice_id.id,
            #     'user_id': self._uid,
            #     'partner_id':self.sale_order_ref.partner_id.id,
            #     'account_id':account_id,
            #     'journal_id':journal_id.id,
            #     'sale_order_ids': [(4,self.sale_order_ref.id)],
            #     'instance_name': str(self.name).encode('utf-8'),
            #     'agreement_id':agreement_order_id.agreement_id.id,
            #     'invoice_type': 'rent',
            # }
            # move_id = invoice_obj.create(invoice_vals)

            ## make invoice line from the agreement product line
            ICPSudo = self.env['ir.config_parameter'].sudo()
            user_product_id = int(ICPSudo.search([('key', '=', 'buy_product')]).value)

            total_days = 0
            to_date = False
            if self.sale_order_ref.invoice_term_id.name == 'Monthly':
                total_days = 30

            if self.sale_order_ref.invoice_term_id.name == 'Yearly':
                total_days = 365
            if total_days:
                to_date = self.exp_date + datetime.timedelta(days=total_days)

            invoice_vals = {
                # 'name': self.env['ir.sequence'].next_by_code('account.payment.customer.invoice') or _('New'),
                'move_type': 'out_invoice',
                'invoice_origin': self.sale_order_ref.name,
                'state': 'draft',
                # 'comment': 'SaaS Recurring Invoice',
                'date': today,
                'invoice_term_id': self.sale_order_ref.invoice_term_id and self.sale_order_ref.invoice_term_id.id,
                # 'address_invoice_id':self.sale_order_ref.partner_invoice_id.id,
                'user_id': self._uid,
                'partner_id': self.sale_order_ref.partner_id.id,

                # 'account_id':account_id,
                'billing': self.billing,
                'journal_id': journal_id.id,
                # 'sale_order_ids': [(4,self.sale_order_ref.id)],
                'instance_name': str(self.name).encode('utf-8'),
                'agreement_id': agreement_order_id.agreement_id.id,
                'no_of_users': agreement_order_id.agreement_id.current_users,
                'invoice_type': 'rent',
                'from_date':self.exp_date,
                'to_date':to_date,
                'invoice_line_ids': [],
            }
            for line in agreement_order_id.agreement_id.agreement_line:
                qty = line.quantity
                months = 1
                if self.sale_order_ref.invoice_term_id.name == 'Yearly':
                    months = 12
                else:
                    months = 1

                # if user_product_id == line.product_id.id:
                #     qty = self.sale_order_ref.no_of_users
                # invoice_line_vals = {
                #                     'name': line.product_id.name,
                #                     'origin': 'SaaS-Kit-'+line.agreement_id.number,
                #                     'move_id': move_id.id,
                #                     'uom_id': line.product_id.uom_id.id,
                #                     'product_id': line.product_id.id,
                #                     'account_id': line.product_id.categ_id.property_account_income_categ_id.id,
                #                     'price_unit': line.product_id.lst_price,
                #                     'discount': line.discount,
                #                     'quantity': qty,
                #                     'account_analytic_id': False,
                #                     }
                # print("___________________111", )
                # print("price unit 44444444444",line.price)
                product_price = line.product_id.get_list_price(partner=self.sale_order_ref.partner_id)
                if line.product_id.id != user_product_id:
                    if self.billing == 'normal' and self.sale_order_ref.invoice_term_id:
                        if self.sale_order_ref.invoice_term_id.type == 'year':
                            total_price = product_price * self.no_of_users * 12
                        elif self.sale_order_ref.invoice_term_id.type == 'from_first_date':
                            total_price = product_price * self.no_of_users
                    else:
                        if self.sale_order_ref.invoice_term_id.type == 'year':
                            total_price = product_price * 12
                        else:
                            total_price = product_price
                else:
                    total_price = product_price

                invoice_line_vals = {
                    'name': line.product_id.name,
                    'price_unit': total_price,
                    # 'price_unit_show': line.product_id.lst_price,
                    'quantity': line.quantity,
                    'product_id': line.product_id.id,

                    # 'product_uom_id': line.product_id.uom_id.id,
                    # 'price_subtotal': line.product_id.lst_price * months * self.sale_order_ref.no_of_users,
                    'tax_ids': [(6, 0, line.product_id.taxes_id.ids)],
                    # 'sale_line_ids': [(6, 0, [so_line.id])],
                    # 'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                    # 'analytic_account_id': False,
                    # 'invoice_line_tax_ids':[[6, False, [line.product_id.taxes_id.id]]]
                }
                invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))

                # if line.product_id.taxes_id.id:
                #     invoice_line_vals['invoice_line_tax_ids'] = [[6, False, [line.product_id.taxes_id.id]]] #[(6, 0, [line.product_id.taxes_id.id])],
            _logger.info('\n\nInvoice vals to pay : {}'.format(invoice_vals))
            inv = invoice_obj.create(invoice_vals)
            if inv:
                inv.action_post()
                ######################################################################
                # Send Mail for customer after creation of invoice
                try:
                    _logger.info('\n\n Created Rent Invoice : \n{} and type : {} '.format(inv, inv.move_type))
                    template = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)
                    if template:
                        lang = template._render_lang(inv.ids)[inv.id]
                    if not lang:
                        lang = get_lang(inv.env).code
                    ctx = dict(
                        default_model='account.move',
                        default_res_id=inv.id,
                        active_ids=inv.ids,
                        active_model='account.move',
                        # For the sake of consistency we need a default_res_model if
                        # default_res_id is set. Not renaming default_model as it can
                        # create many side-effects.
                        default_res_model='account.move',
                        default_use_template=bool(template),
                        default_template_id=template and template.id or False,
                        default_composition_mode='comment',
                        mark_invoice_as_sent=True,
                        custom_layout="mail.mail_notification_paynow",
                        model_description=inv.with_context(lang=lang).type_name,
                        force_email=True
                    )

                    send_invoice_mail = self.env['account.invoice.send'].with_context(ctx).create({
                        'partner_ids': inv.partner_id,
                        'is_print': True,
                        'is_email': True
                    })

                    send_invoice_mail.composer_id._onchange_template_id_wrapper()
                    _logger.info('\n\n ____ Invoice Sent Wizard1 : \n{}'.format(send_invoice_mail))
                    sent_flag = send_invoice_mail._send_email()
                    _logger.info('\n\n ____ Invoice Sent Wizard2 : \n{}'.format(sent_flag))
                except Exception as e:
                    _logger.error('\n\nError while Sending Email : {}'.format(e))
                ###################################################################################

                # sequence = inv._get_sequence_format_param(inv.name)
                # name1 = sequence.next_by_id(sequence_date=inv.date)
                # inv.name = name1

            # recompute taxes(Update taxes)
            # if move_id.invoice_line_ids: move_id.compute_taxes()
        #     return move_id
        #
        # #recompute taxes(Update taxes)
        # print (move_id,'====================================ss')
        # if move_id:
        #     if move_id.invoice_line_ids: move_id.compute_taxes()
        return move_id

    # added by krishna
    def send_saas_alert_email(self, alert_type):
        alert_no_of_days = 0
        result = False
        today = time.strftime('%Y-%m-%d')
        ICPSudo = self.env['ir.config_parameter'].sudo()

        if alert_type == 'free_trial':
            alert_no_of_days = int(ICPSudo.get_param('free_trail_no_of_days', default=7))
        elif alert_type == 'expire_db':
            alert_no_of_days = int(ICPSudo.get_param('db_expire_no_of_days', default=7))

        if str(self.exp_date) == str(datetime.datetime.now().date()):
            _logger.info('SaaS-Tenant %(db)s db expire today' % {'db': self.name})

            mail_template_id = self.env.ref('saas_base.email_template_renew_tenant_Expired_today',
                                            raise_if_not_found=False)
            result = mail_template_id.with_context(lang=self.sale_order_ref.partner_id.lang).send_mail(self.id,
                                                                                                       force_send=True,
                                                                                                       )

        if alert_no_of_days > 0:
            alertday = str(datetime.datetime.strptime(str(self.exp_date), '%Y-%m-%d') - datetime.timedelta(
                days=int(alert_no_of_days)))[:10]
            if (alertday == str(today)):
                _logger.info('SaaS-Invoice Generated for Tenant %(db)s' % {'db': self.name})
                _logger.info('\n\nSale order Partner : \n{} \n\n'.format(self.sale_order_ref.partner_id))

                mail_template_id = self.env.ref('saas_base.email_template_renew_tenant_subscription_alert',
                                                raise_if_not_found=False)
                result = mail_template_id.with_context(lang=self.sale_order_ref.partner_id.lang).send_mail(self.id,
                                                                                                           force_send=True,
                                                                                                           )
        if alert_type == 'grace_period_start':
            _logger.info('SaaS-Tenant %(db)s grace period started' % {'db': self.name})

            mail_template_id = self.env.ref('saas_base.email_template_tenant_db_grace_alert', raise_if_not_found=False)
            result = mail_template_id.with_context(lang=self.sale_order_ref.partner_id.lang).send_mail(self.id,
                                                                                                       force_send=True)

        ## if alert type is grace_period_start send email to tenant that database is ready to purge         
        if alert_type == 'ready_for_purge':
            _logger.info('SaaS-Tenant %(db)s ready to purge' % {'db': self.name})
            mail_template_id = self.env.ref('saas_base.email_template_tenant_db_purge_alert', raise_if_not_found=False)
            result = mail_template_id.with_context(lang=self.sale_order_ref.partner_id.lang).send_mail(self.id,
                                                                                                       force_send=True)

        return result

    def init(self):
        cr = self._cr
        expired_db_role = 'expired_db_owner'
        bare_db = 'bare_tenant_17'
        db_name = 'saasmaster_v17'
        cr.execute("SELECT 1 FROM pg_roles WHERE rolname='%(role)s'" % {'role': expired_db_role})
        role_exist = cr.fetchone()
        config['expired_db_owner'] = ""
        config['bare_db'] = ""
        config['db_name'] = ""

        if not role_exist:
            cr.execute("create role %(role)s" % {'role': expired_db_role})
            config.__setitem__('expired_db_owner', expired_db_role)
            config.save()
            _logger.info('SaaS- Expired DB Role %(role)s created' % {'role': expired_db_role})
        else:
            config.__setitem__('expired_db_owner', expired_db_role)
            config.save()
        cr.execute("SELECT datname FROM pg_database WHERE datname='%(db)s'" % {'db': bare_db})
        db_exist = cr.fetchone()
        if not db_exist:
            db.exp_create_database(bare_db, False, 'en_US', 'admin')
            import odoo
            from odoo.api import Environment
            registry = odoo.registry(bare_db)
            with closing(registry.cursor()) as bare_cr:
                env = Environment(bare_cr, ADMINUSER_ID, {})
                module_obj = env['ir.module.module'].sudo()
                module_ids_to_install = module_obj.sudo().search([('name', 'in', ['base'])])
                try:
                    for mod_install in module_ids_to_install:
                        mod_install.sudo().button_immediate_install()
                except Exception as e:
                    print(e)

            config.__setitem__('bare_db', bare_db)
            config.__setitem__('db_name', db_name)
            config.save()
            _logger.info('SaaS- Bare Database %(db)s created' % {'db': bare_db})
        else:
            config.__setitem__('bare_db', bare_db)
            config.__setitem__('db_name', db_name)
            config.save()

    def create_rent_invoice_manualy(self):
        print("---create_rent_invoice_manualy")
        tenant_db = self
        so_origin = tenant_db.sale_order_ref.name
        ## If found any, allow to expire DB, bcoz grace period is over and still invoices are not paid
        related_invoice_ids = self.env['account.move'].search(
            [('invoice_origin', '=', so_origin), ('invoice_type', '=', 'rent'),
             ('state', 'in', ['draft', 'posted'])])
        # print('\n\nrelated invoices : ', related_invoice_ids)
        # if not related_invoice_ids:
        # create invoice for the first time if moved to grace stage
        move_id = tenant_db._make_invoice()
        if move_id:
            # move invoice in "Open" state
            if move_id.invoice_line_ids: move_id.action_post()
        # else:
        #     raise ValidationError('Invoice is already present')

    def check_tenant_database_expire(self):
        """
        Overridden as it is
        """
        try:
            _logger.info('SaaS-Db Expire db check start')
            cr = self._cr

            # Find all databases list available
            server_db_list = []
            cr.execute("select datname from pg_database where datistemplate=false")
            cr_res = cr.fetchall()
            for item in cr_res:
                if item:
                    server_db_list.append(item[0])
            import datetime
            today = datetime.datetime.now().date()
            tenant_list = self.env['tenant.database.list'].sudo().search([])
            if tenant_list:
                for tenant_db in tenant_list:
                    print("\n==========================Start=============================================",
                          tenant_db.name, tenant_db.stage_id.name, tenant_db.free_trial)
                    if tenant_db.stage_id.name != 'Terminated':
                        # if tenant_db.name == 'teljlksdf':
                        # Find configured grace and purging days
                        ICPSudo = self.env['ir.config_parameter'].sudo()
                        grace_days = int(ICPSudo.search([('key', '=', 'grace_period')]).value)
                        # purge_days = int(ICPSudo.search([('key', '=', 'data_purging_days')]).value)
                        # print("1"*88,purge_days)
                        # if not tenant_db.expired:
                        # Pulled outside of this if statement and if statement commented
                        # ==========================Start=============================================
                        ## check tenant database is in free trail or not
                        if tenant_db.free_trial:
                            tenant_db.send_saas_alert_email('free_trial')
                        else:
                            tenant_db.send_saas_alert_email('expire_db')

                        ##check if db state in [active,grace,expired]
                        in_allowed_stages = False
                        if tenant_db.stage_id.is_active or tenant_db.stage_id.is_grace:  # or tenant_db.stage_id.is_expired:
                            in_allowed_stages = True

                        if in_allowed_stages:

                            ## if tenant database exp_date plus grace days is equal to today then deactivate database. Set stage to 'Expired'
                            ##------------------------------Start--------------------------------------------
                            graceperiod_date = str(
                                datetime.datetime.strptime(str(tenant_db.exp_date), '%Y-%m-%d') - datetime.timedelta(
                                    days=int(grace_days)))[
                                               :10]
                            # print('\n\ngraceperiod_Date : ', graceperiod_date)

                            # graceperiod_date has format (y-m-d)
                            graceperiod_date = graceperiod_date.split('-')
                            y = graceperiod_date[0]
                            m = graceperiod_date[1]
                            d = graceperiod_date[2]
                            graceperiod_date = datetime.datetime.strptime(d + '' + m + '' + y, '%d%m%Y').date()
                            print("\n\ndatabase Name : ", tenant_db.exp_date, tenant_db.name, 'graceperiod_Date : ',
                                  graceperiod_date, 'today : ', today)

                            grace_stage_id = self.env['tenant.database.stage'].search([('is_grace', '=', True)],
                                                                                      limit=1)
                            if tenant_db.stage_id.is_active:
                                so_origin = tenant_db.sale_order_ref.name
                                ## Find related invoice ids which are in draft and open state
                                ## If found any, allow to expire DB, bcoz grace period is over and still invoices are not paid
                                related_invoice_ids = self.env['account.move'].search(
                                    [('invoice_origin', '=', so_origin), ('invoice_type', '=', 'rent'),
                                     ('state', 'in', ['draft', 'posted'])])
                                print('\n\nrelated invoices : ', related_invoice_ids)
                                # if today is grace period date then generate the invoice
                                if graceperiod_date <= today:
                                    # create invoice for the first time if moved to grace stage
                                    move_id = tenant_db._make_invoice()
                                    if move_id:
                                        # move invoice in "Open" state
                                        if move_id.invoice_line_ids:
                                            move_id.action_post()
                                    tenant_db.write({'stage_id': grace_stage_id.id})


                            # Send grace period mail in grace period
                            if tenant_db.stage_id.is_grace:
                                try:
                                    tenant_db.send_saas_alert_email('grace_period_start')
                                except Exception as e:
                                    print(e)

                            # Check id database expiry date is increased from todays date
                            expiry_date = tenant_db.exp_date
                            if expiry_date <= today and tenant_db.name in server_db_list:
                                stage_ids = self.env['tenant.database.stage'].search([('is_expired', '=', True)],
                                                                                     limit=1)

                                tenant_db.write({'stage_id': stage_ids.id if stage_ids else False})

                                # cr.execute("ALTER DATABASE %(db)s OWNER TO %(role)s" % {'db': tenant_db.name,
                                #                                                         'role': 'expired_db_owner'})

                                brand_website = ICPSudo.search([('key', '=', 'brand_website')]).value
                                brand_admin = ICPSudo.search([('key', '=', 'admin_login')]).value
                                brand_pwd = ICPSudo.search([('key', '=', 'admin_pwd')]).value
                                db_name = tenant_db.name
                                dest_model = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(brand_website))
                                common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(brand_website))
                                uid_dst = common.authenticate(db_name, brand_admin, brand_pwd, {})
                                db_expire = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'db.expire', 'search',
                                                                  [[]])

                                for msg in db_expire:
                                    dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'db.expire', 'write',
                                                          [msg,
                                                           {
                                                               'db_expire': True,
                                                           }]
                                                          )
                                tenant_db.send_saas_alert_email('expired')
                            ##-----------------------------End-------------------------------------------------
                        print("2" * 88, tenant_db.stage_id, tenant_db.stage_id.is_expired)
                        # if tenant_db.stage_id.is_expired:
                        #     ##data purge email
                        #     #send mail before 2 days from puging
                        #     if purge_days > 3:
                        #         mail_days = int(purge_days) - 3
                        #     else:
                        #         mail_days = 0
                        #     print("3"*88,mail_days)
                        #     # compute date for mail triggering for mail before two days for puging date
                        #     purge_mail_date = str(datetime.datetime.strptime(str(tenant_db.exp_date), '%Y-%m-%d') + datetime.timedelta(
                        #         days=mail_days))[:10]
                        #     print("4"*88,purge_mail_date)
                        #     purge_mail_date = purge_mail_date.split('-')
                        #     print("5"*88,purge_mail_date)
                        #     purge_mail_date = datetime.datetime.strptime(purge_mail_date[2] + '' + purge_mail_date[1] + '' + purge_mail_date[0], '%d%m%Y').date()
                        #     print("6"*88,purge_mail_date)
                        #     # compute date for purging database
                        #     purge_date = str(datetime.datetime.strptime(str(tenant_db.exp_date), '%Y-%m-%d') + datetime.timedelta(
                        #         days=purge_days))[:10]
                        #     print("7"*88,purge_date)
                        #     purge_date = purge_date.split('-')
                        #     print("8"*88,purge_date)
                        #     # y = purge_date[0]
                        #     # m = purge_date[1]
                        #     # d = purge_date[2]
                        #     purge_date = datetime.datetime.strptime(purge_date[2] + '' + purge_date[1] + '' + purge_date[0], '%d%m%Y').date()
                        #     _logger.info(_('\n\n\npurge days : {} purge mail days : {}'.format(purge_days, mail_days)))
                        #     _logger.info(_("\n\n\npurge date : {} purge mail date : {}".format(purge_date, purge_mail_date)))
                        #     if str(purge_mail_date) <= str(today) < str(purge_date):
                        #         tenant_db.send_saas_alert_email('ready_for_purge')

                        # if str(purge_date) == str(today):
                        #     #######################################################################3
                        #     agreement_obj = self.env['sale.recurring.orders.agreement'].sudo()
                        #     db_name = tenant_db.name
                        #     cr = self._cr

                        #     # deactivate DB
                        #     stage_ids = self.env['tenant.database.stage'].search([('is_purge', '=', True)])
                        #     tenant_db.write({'stage_id': stage_ids[0].id if stage_ids else False})

                        #     # deactivate agreements
                        #     agreement_ids = agreement_obj.search([('order_line.order_id.instance_name', '=', str(db_name))])

                        #     agreement_ids.write({'active': False})

                        #     # cr.execute("""UPDATE pg_database SET datallowconn = 'false' WHERE datname = '%s';"""%db_name)
                        #     # cr.execute("""ALTER DATABASE %s CONNECTION LIMIT 1;"""%db_name)

                        #     cr.execute("""SELECT pg_terminate_backend(pid)
                        #      FROM pg_stat_get_activity(NULL::integer)
                        #      WHERE datid=(SELECT oid from pg_database where datname = '%s');""" % db_name)

                        #     cr.execute(
                        #         "ALTER DATABASE %(db)s OWNER TO %(role)s" % {'db': tenant_db.name, 'role': 'expired_db_owner'})
                        #######################################################################3
            else:
                _logger.info('No any tenant found for action')
        except Exception as e:
            _logger.error('Error : {}'.format(e))

        _logger.info('SaaS-Db Expire db check end')
        return True

    def _get_grace_period_date(self):
        """
        Get grace period expiration date of the agreement.
        """
        for tenant_db in self:
            ICPSudo = self.env['ir.config_parameter'].sudo()
            grace_days = int(ICPSudo.search([('key', '=', 'grace_period')]).value)
            self.grace_period_date = str(
                datetime.datetime.strptime(str(tenant_db.exp_date), '%Y-%m-%d') + datetime.timedelta(
                    days=int(grace_days)))[
                                     :10]
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'invoice_term_id' in vals:
                del vals['invoice_term_id']
                if 'free_trial' in vals and vals['free_trial']:
                    vals['next_invoice_create_date'] = vals['exp_date']
        return super(tenant_database_list, self).create(vals_list)

    def get_tenant_url(self):
        for o in self:
            so = o.sale_order_ref
            if so:
                ICPSudo = self.env['ir.config_parameter'].sudo()
                domain = ICPSudo.search([('key', '=', 'domain_name')]).value
                if not domain.startswith('.'):
                    domain = '.' + domain

                o.tenant_url = "%s%s" % (so.instance_name, domain)

    name = fields.Char('DB Name', size=64, index=True, translate = True)
    exp_date = fields.Date('Expiry Date')
    next_invoice_create_date = fields.Date('Next invoice create date')
    expired = fields.Boolean('Terminated / Deactivated')
    free_trial = fields.Boolean('Free Trial')
    sale_order_ref = fields.Many2one('sale.order', 'Sale Order Ref.')
    no_of_users = fields.Integer('No of Users', default=1)
    active = fields.Boolean('Active', default=True)
    grace_period_date = fields.Date(compute='_get_grace_period_date', string='Grace Period Date')
    user_id = fields.Many2one('res.users', 'User', readonly=True)
    reason = fields.Text('Reason')
    deactivated_date = fields.Date('Deactivated Date')

    billing = fields.Selection([('normal', 'Per Module/Per Month/Per User'),
                                ('user_plan_price', 'Users + Plan Price')
                                ], string="Billing Type", default="normal")

    stage_id = fields.Many2one('tenant.database.stage', 'Stage', index=True,
                               domain="[]")
    color = fields.Integer('Color Index', default=0)
    user_login = fields.Char('User Login', size=64)
    user_pwd = fields.Char('User Password', size=64)
    super_user_login = fields.Char('Super User Login', size=64)
    super_user_pwd = fields.Char('Super User Password', size=64)
    tenant_url = fields.Char(compute='get_tenant_url', string='Tenant URL')
    user_history_ids = fields.One2many('user.history', 'tenant_id', string="Users History")
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
                                 default=lambda self: self.env.company)


class UserHistory(models.Model):
    _name = 'user.history'
    _description = 'User History'

    rec_date = fields.Date("Date")
    pre_users = fields.Integer("Previous Count")
    adding = fields.Integer("TO add")
    total = fields.Integer("Current Total")
    tenant_id = fields.Many2one('tenant.database.list', string='Tenant')
