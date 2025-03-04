# -*- coding: utf-8 -*-
from odoo import fields
import datetime
import odoo
from odoo.api import Environment
from odoo import _
from functools import partial
from odoo.tools.misc import formatLang
from odoo.tools import config
import logging
import time
from odoo.service import db
from odoo.tools.float_utils import float_round as round
from odoo import api, models
import xmlrpc
from odoo.exceptions import UserError
import traceback
from odoo.http import request
from odoo.addons.website_sale.models.website import Website
import psycopg2
from contextlib import closing
import json


class AccountMove(models.Model):
    _inherit = 'account.move'
    """ inherited to add some new fields"""

    billing = fields.Selection([('normal', 'Per Module/Per Month/Per User'),
                                ('user_plan_price', 'Users + Plan Price')
                                ], string="Billing Type", default="normal")
    saas_order = fields.Boolean(string='SaaS Order', default=False)
    instance_name = fields.Char('Database Name', size=64)
    no_of_users = fields.Integer('No. of Users', default=1)
    invoice_term_id = fields.Many2one('recurring.term', 'Invoicing Term')
    invoice_type = fields.Selection([('rent', 'Rent Invoice'), ('user', 'User Purchase Invoice')],
                                    string="Invoice Type")
    expiry_date = fields.Date(compute='_get_expiry', string="Expiry Date")
    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")

    def _get_expiry(self):

        for item in self:

            db = self.env['tenant.database.list'].search([('name', '=', item.instance_name)], limit=1)
            if db:
                item.expiry_date = db.exp_date

    def button_proforma_voucher(self, conText=None):
        res = super(AccountMove, self).button_proforma_voucher(conText)
        invoice_obj = self.env['account.move']
        tenant_db_list_obj = self.env['tenant.database.list']
        config = odoo.tools.config
        db_name = str(invoice_obj.browse(conText['move_id']).instance_name)
        invoice = invoice_obj.browse(conText['move_id'])

        agreement = self.env['sale.recurring.orders.agreement'].sudo().search([('instance_name', '=', db_name)])
        if not agreement:
            return res

        #         if invoice.instance_name and invoice.amount_total != 0.00:
        #              """Code for Trial Expiry"""
        ## if the invoice amt is 0 then direct return
        tenant_db_id = tenant_db_list_obj.search([('name', '=', db_name)])
        tenant_db = tenant_db_list_obj.browse(tenant_db_id)
        if type(tenant_db) is list:
            tenant_db = tenant_db[0]
        #             old_exp_date = tenant_db[0].exp_date
        #         old_exp_date = tenant_db[0].next_invoice_create_date

        ##for different subscription terms take respective No .of months
        months_to_add = 0
        term_type = tenant_db.invoice_term_id.type
        if term_type == 'from_first_date': months_to_add = 1
        if term_type == 'quarter': months_to_add = 3
        if term_type == 'half_year': months_to_add = 6
        if term_type == 'year': months_to_add = 12

        #             new_exp_date = str(mx.DateTime.strptime(str(old_exp_date),'%Y-%m-%d') + RelativeDateTime(months=months_to_add))[:10]

        ##If all pending invoices paid, allow to active db
        allow_to_active_db = True

        sale_id = self.env['sale.order'].search([('instance_name', '=', db_name)], limit=1)
        if sale_id:
            so_name = sale_id.name
            draft_invoices_ids_so = invoice_obj.search([('invoice_origin', '=', so_name), ('state', '!=', 'posted')])
            if draft_invoices_ids_so:
                allow_to_active_db = False

        if allow_to_active_db:
            # if tenant_db[0].expired:
            #                 new_exp_date = str(mx.DateTime.strptime(str(old_exp_date),'%Y-%m-%d') + RelativeDateTime(months=months_to_add))[:10]
            new_exp_date = False  ##tenant_db[0].next_invoice_create_date

            ## In case if tenant DB doesn't have 'next_invoice_create_date' date, 'new_exp_date' will set to blank
            ## To avoid this calculate tenant's 'new_exp_date' from it's subscription term.
            if not new_exp_date:
                ##If subscription period is monthly and 3 invoices are missed.
                ##In this case we added 3 months to get 'new_exp_date', i.e. 'new_exp_date' should be greater than Today's date
                new_exp_date = tenant_db.exp_date
                while True:
                    new_exp_date = str(datetime.datetime.strptime(str(new_exp_date), '%Y-%m-%d') + datetime.timedelta(
                        months=months_to_add))[:10]
                    new_exp_date = new_exp_date.split('-')
                    y = new_exp_date[0]
                    m = new_exp_date[1]
                    d = new_exp_date[2]
                    new_exp_date = datetime.datetime.strptime(d + '' + m + '' + y, '%d%m%Y').date()
                    today = datetime.datetime.now().date()
                    if new_exp_date > today:
                        break

            self._cr.execute("ALTER DATABASE %(db)s OWNER TO %(role)s" % {'db': db_name, 'role': config['db_user']})
            active_stage_id = self.env['tenant.database.stage'].search([('is_active', '=', True)], limit=1)
            tenant_db_list_obj.write([tenant_db.id], {'free_trial': False,
                                                      'expired': False,
                                                      'exp_date': new_exp_date,
                                                      'stage_id': active_stage_id.id if active_stage_id else False
                                                      })

            db = self
            pool = self
            with closing(db.cursor()) as slave_cr:
                saas_service_obj_ids = pool.get('saas.service').sudo().search(slave_cr, ADMINUSER_ID, [])
                pool.get('saas.service').sudo().write(slave_cr, ADMINUSER_ID, saas_service_obj_ids,
                                                      {'expiry_date': new_exp_date})
                slave_cr.commit()

        email_template_obj = self.env['mail.template']
        mail_template_id = self.env['ir.model.data']._xmlid_to_res_id(
            'openerp_saas_instance', 'email_template_renew_subscription')

        #         email_template_obj.send_mail(  mail_template_id[1], tenant_db.id, force_send=True,conText=conText)
        mail_template_id.send_mail(tenant_db.id, force_send=True)
        return res

    def _recompute_tax_lines(self, recompute_tax_base_amount=False):
        ''' Compute the dynamic tax lines of the journal entry.

        :param lines_map: The line_ids dispatched by type containing:
            * base_lines: The lines having a tax_ids set.
            * tax_lines: The lines having a tax_line_id set.
            * terms_lines: The lines generated by the payment terms of the invoice.
            * rounding_lines: The cash rounding lines of the invoice.
        '''
        self.ensure_one()
        in_draft_mode = self != self._origin

        def _serialize_tax_grouping_key(grouping_dict):
            ''' Serialize the dictionary values to be used in the taxes_map.
            :param grouping_dict: The values returned by '_get_tax_grouping_key_from_tax_line' or '_get_tax_grouping_key_from_base_line'.
            :return: A string representing the values.
            '''
            return '-'.join(str(v) for v in grouping_dict.values())

        def _compute_base_line_taxes(base_line):
            ''' Compute taxes amounts both in company currency / foreign currency as the ratio between
            amount_currency & balance could not be the same as the expected currency rate.
            The 'amount_currency' value will be set on compute_all(...)['taxes'] in multi-currency.
            :param base_line:   The account.move.line owning the taxes.
            :return:            The result of the compute_all method.
            '''
            move = base_line.move_id

            if move.is_invoice(include_receipts=True):
                handle_price_include = True
                sign = -1 if move.is_inbound() else 1

                # //////////////////////////
                if move.billing == 'normal':
                    quantity = base_line.quantity * base_line.no_of_users * base_line.month
                else:
                    quantity = base_line.quantity * base_line.month
                # ///////////////////

                is_refund = move.move_type in ('out_refund', 'in_refund')
                price_unit_wo_discount = sign * base_line.price_unit * (1 - (base_line.discount / 100.0))
            else:
                handle_price_include = False
                quantity = 1.0
                tax_type = base_line.tax_ids[0].type_tax_use if base_line.tax_ids else None
                is_refund = (tax_type == 'sale' and base_line.debit) or (tax_type == 'purchase' and base_line.credit)
                price_unit_wo_discount = base_line.amount_currency

            # ////////////////////////////////////////////////////////////// recomputing taxes on basis of months
            payment_term = self.invoice_term_id

            # months = 1
            # if base_line.calculate_field:
            #     if payment_term:
            #         if payment_term.name == 'Yearly':
            #             months = 12
            #             base_line.calculate_field = False

            # /////////////////////////////////////////////////////////////////

            print('\n\n00000000000000000000000000\n\n{}'.format(quantity))
            return base_line.tax_ids._origin.with_context(force_sign=move._get_tax_force_sign()).compute_all(
                price_unit_wo_discount,
                currency=base_line.currency_id,
                quantity=quantity,
                product=base_line.product_id,
                partner=base_line.partner_id,
                is_refund=is_refund,
                handle_price_include=handle_price_include,
                include_caba_tags=move.always_tax_exigible,
                users=1.0,
                # months=months
            )

        taxes_map = {}

        # ==== Add tax lines ====
        to_remove = self.env['account.move.line']
        for line in self.line_ids.filtered('tax_repartition_line_id'):
            grouping_dict = self._get_tax_grouping_key_from_tax_line(line)
            grouping_key = _serialize_tax_grouping_key(grouping_dict)
            if grouping_key in taxes_map:
                # A line with the same key does already exist, we only need one
                # to modify it; we have to drop this one.
                to_remove += line
            else:
                taxes_map[grouping_key] = {
                    'tax_line': line,
                    'amount': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                }
        if not recompute_tax_base_amount:
            self.line_ids -= to_remove

        # ==== Mount base lines ====
        for line in self.line_ids.filtered(lambda line: not line.tax_repartition_line_id):
            # Don't call compute_all if there is no tax.
            if not line.tax_ids:
                if not recompute_tax_base_amount:
                    line.tax_tag_ids = [(5, 0, 0)]
                continue

            compute_all_vals = _compute_base_line_taxes(line)

            # Assign tags on base line
            if not recompute_tax_base_amount:
                line.tax_tag_ids = compute_all_vals['base_tags'] or [(5, 0, 0)]

            for tax_vals in compute_all_vals['taxes']:
                grouping_dict = self._get_tax_grouping_key_from_base_line(line, tax_vals)
                grouping_key = _serialize_tax_grouping_key(grouping_dict)

                tax_repartition_line = self.env['account.tax.repartition.line'].browse(
                    tax_vals['tax_repartition_line_id'])
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id

                taxes_map_entry = taxes_map.setdefault(grouping_key, {
                    'tax_line': None,
                    'amount': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                })
                taxes_map_entry['amount'] += tax_vals['amount']
                taxes_map_entry['tax_base_amount'] += self._get_base_amount_to_display(tax_vals['base'],
                                                                                       tax_repartition_line,
                                                                                       tax_vals['group'])
                taxes_map_entry['grouping_dict'] = grouping_dict

        # ==== Pre-process taxes_map ====
        taxes_map = self._preprocess_taxes_map(taxes_map)

        # ==== Process taxes_map ====
        for taxes_map_entry in taxes_map.values():
            # The tax line is no longer used in any base lines, drop it.
            if taxes_map_entry['tax_line'] and not taxes_map_entry['grouping_dict']:
                if not recompute_tax_base_amount:
                    self.line_ids -= taxes_map_entry['tax_line']
                continue

            currency = self.env['res.currency'].browse(taxes_map_entry['grouping_dict']['currency_id'])

            # Don't create tax lines with zero balance.
            if currency.is_zero(taxes_map_entry['amount']):
                if taxes_map_entry['tax_line'] and not recompute_tax_base_amount:
                    self.line_ids -= taxes_map_entry['tax_line']
                continue

            # tax_base_amount field is expressed using the company currency.
            tax_base_amount = currency._convert(taxes_map_entry['tax_base_amount'], self.company_currency_id,
                                                self.company_id, self.date or fields.Date.context_today(self))

            # Recompute only the tax_base_amount.
            if recompute_tax_base_amount:
                if taxes_map_entry['tax_line']:
                    taxes_map_entry['tax_line'].tax_base_amount = tax_base_amount
                continue

            balance = currency._convert(
                taxes_map_entry['amount'],
                self.company_currency_id,
                self.company_id,
                self.date or fields.Date.context_today(self),
            )
            to_write_on_line = {
                'amount_currency': taxes_map_entry['amount'],
                'currency_id': taxes_map_entry['grouping_dict']['currency_id'],
                'debit': balance > 0.0 and balance or 0.0,
                'credit': balance < 0.0 and -balance or 0.0,
                'tax_base_amount': tax_base_amount,
            }

            if taxes_map_entry['tax_line']:
                # Update an existing tax line.
                taxes_map_entry['tax_line'].update(to_write_on_line)
            else:
                create_method = in_draft_mode and self.env['account.move.line'].new or self.env[
                    'account.move.line'].create
                tax_repartition_line_id = taxes_map_entry['grouping_dict']['tax_repartition_line_id']
                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_repartition_line_id)
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id
                taxes_map_entry['tax_line'] = create_method({
                    **to_write_on_line,
                    'name': tax.name,
                    'move_id': self.id,
                    'partner_id': line.partner_id.id,
                    'company_id': line.company_id.id,
                    'company_currency_id': line.company_currency_id.id,
                    'tax_base_amount': tax_base_amount,
                    'exclude_from_invoice_tab': True,
                    **taxes_map_entry['grouping_dict'],
                })

            if in_draft_mode:
                taxes_map_entry['tax_line'].update(
                    taxes_map_entry['tax_line']._get_fields_onchange_balance(force_computation=True))



    def get_invoice_period(self):
        for rec in self:
            invoice_period = ''
            if rec.from_date and rec.to_date:
                invoice_period = str(rec.from_date.strftime("%d/%m/%Y")) + ' - ' + str(
                    rec.to_date.strftime("%d/%m/%Y"))
            return invoice_period


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    """Inherited For calculate the subtotal price in invoice line with number of users"""

    month = fields.Integer(string='Invoice Term', default=1)
    no_of_users = fields.Integer(string='Users', default=1)
    billing = fields.Selection([('normal', 'Per Module/Per Month/Per User'),
                                ('user_plan_price', 'Users + Plan Price')
                                ], string="Billing Type", default="normal")
    calculate_field = fields.Boolean('yes', default=True)

    @api.model
    def _get_fields_onchange_balance_model(self, quantity, discount, amount_currency, move_type, currency, taxes,
                                           price_subtotal, force_computation=False):
        ''' This method is inherited to compute the invoice line total with saas values '''
        super(AccountMoveLine, self)._get_fields_onchange_balance_model(quantity=quantity, discount=discount,
                                                                        amount_currency=amount_currency,
                                                                        move_type=move_type, currency=currency,
                                                                        taxes=taxes, price_subtotal=price_subtotal,
                                                                        force_computation=force_computation)
        if move_type in self.move_id.get_outbound_types():
            sign = 1
        elif move_type in self.move_id.get_inbound_types():
            sign = -1
        else:
            sign = 1
        amount_currency *= sign

        # if not month:
        month = self.month or 1
        no_of_users = self.no_of_users or 1

        if not force_computation and currency.is_zero(amount_currency - price_subtotal):
            return {}

        taxes = taxes.flatten_taxes_hierarchy()
        if taxes and any(tax.price_include for tax in taxes):
            force_sign = -1 if move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1
            taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(amount_currency,
                                                                                      currency=currency,
                                                                                      handle_price_include=False)
            print('Tax RES : {} '.format(taxes_res))
            for tax_res in taxes_res['taxes']:
                tax = self.env['account.tax'].browse(tax_res['id'])
                if tax.price_include:
                    amount_currency += tax_res['amount']

        discount_factor = 1 - (discount / 100.0)
        if amount_currency and discount_factor:
            # discount != 100%
            vals = {
                'quantity': quantity or 1.0,
                'price_unit': amount_currency / discount_factor / ((quantity * month * no_of_users) or 1.0)
            }
        elif amount_currency and not discount_factor:
            # discount == 100%
            vals = {
                'quantity': quantity or 1.0,
                'discount': 0.0,
                'price_unit': amount_currency / ((quantity * month * no_of_users) or 1.0),
            }
        elif not discount_factor:
            # balance of line is 0, but discount  == 100% so we display the normal unit_price
            vals = {}
        else:
            # balance is 0, so unit price is 0 as well
            vals = {'price_unit': 0.0}

        print('========================================== {}'.format(vals))
        return vals
