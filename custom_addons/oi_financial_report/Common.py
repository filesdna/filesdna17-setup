'''
Created on Oct 24, 2016

@author: Zuhair
'''

from odoo import fields, models
from datetime import timedelta
import sys
PY2 = sys.version_info[0] == 2

if PY2:
    string_types = (str, unicode)  # @UndefinedVariable
else:
    string_types = (str, )

SQL_FROM ="""
FROM account_move
INNER JOIN account_move_line ON (account_move_line.move_id = account_move.id and account_move.state<>'cancel')
INNER JOIN res_company ON (res_company.id = account_move.company_id)
LEFT JOIN account_journal ON (account_journal.id = account_move.journal_id)
LEFT JOIN account_account ON (account_account.id = account_move_line.account_id)
LEFT JOIN oi_fin_account_type as account_type ON (account_type.value = account_account.account_type)
LEFT JOIN res_partner ON (res_partner.id = account_move_line.partner_id)
LEFT JOIN res_country ON (res_country.id = res_partner.country_id)
LEFT JOIN product_product ON (product_product.id = account_move_line.product_id)
LEFT JOIN product_template ON (product_template.id = product_product.product_tmpl_id)
LEFT JOIN product_category ON (product_category.id = product_template.categ_id)
LEFT JOIN uom_uom ON (uom_uom.id = account_move_line.product_uom_id)
LEFT JOIN account_bank_statement_line ON (account_bank_statement_line.id = account_move_line.statement_line_id)
LEFT JOIN account_bank_statement ON (account_bank_statement.id = account_bank_statement_line.statement_id)
LEFT JOIN account_group ON (account_group.id = account_account.group_id)
"""
SQL_FROM_BUDGET ="""
FROM account_budget_move as account_move
INNER JOIN account_budget_move_line account_move_line ON (account_move_line.move_id = account_move.id)
INNER JOIN account_budget_rel ON (account_move_line.general_budget_id = account_budget_rel.budget_id)
INNER JOIN res_company ON (res_company.id = account_move.company_id)
--LEFT JOIN account_journal ON (account_journal.id = account_move.journal_id)
LEFT JOIN account_account ON (account_account.id = account_budget_rel.account_id)
LEFT JOIN oi_fin_account_type as account_type  ON (account_type.value = account_account.account_type)
--LEFT JOIN res_partner ON (res_partner.id = account_move_line.partner_id)
--LEFT JOIN res_country ON (res_country.id = res_partner.country_id)
--LEFT JOIN product_product ON (product_product.id = account_move_line.product_id)
--LEFT JOIN product_template ON (product_template.id = product_product.product_tmpl_id)
--LEFT JOIN product_category ON (product_category.id = product_template.categ_id)
--LEFT JOIN uom_uom ON (uom_uom.id = account_move_line.product_uom_id)
--LEFT JOIN account_bank_statement_line ON (account_bank_statement_line.id = account_move_line.statement_line_id)
--LEFT JOIN account_bank_statement ON (account_bank_statement.id = account_bank_statement_line.statement_id)
LEFT JOIN account_group ON (account_group.id = account_account.group_id)
"""

PERIODS = {
    'day': dict(),
    'month': dict(day=1),
    'year': dict(day=1, month=1),
}
ODD_PERIODS = ['week', 'quarter', 'half_year']

SUMMARY_FUNCTIONS = [('SUM','Sum'),
                     ('AVERAGE','Average'),
                     ('MIN','Minimum'),
                     ('MAX','Maximum'),
                     ('VAR.P','Population Variance (VAR.P)'),
                     ('VAR.S','Sample Variance (VAR.S)'),
                     ('STDEV.P','Population Standard Deviation (STDEV.P)'),
                     ('STDEV.S','Sample Standard Deviation (STDEV.S)'),
                     ('DEVSQ','Squared Deviation (DEVSQ)'),
                     ('AVEDEV','Average Absolute Deviation (AVEDEV)'),
                     ('MAD','Median Absolute Deviation (MAD)'),
                     ]


def extract_ids(records):
    "extract first item from list records"
    return tuple(record[0] for record in records)

def get_date_str(value):
    if isinstance(value, string_types):
        return value
    return fields.Date.to_string(value)

def get_sql_value(obj, sql, para = tuple()):
    cr=obj.env.cr if isinstance(obj, models.BaseModel) else obj
    cr.execute(sql, para)
    row =cr.fetchone()
    if row:
        return row[0]
    
def get_sql_date(obj, sql, para = tuple()):
    dt = get_sql_value(obj,sql,para)
    if isinstance(dt, string_types):
        dt = fields.Date.from_string(dt)
    return dt

def get_sql_ids(obj, sql, para = tuple()):
    cr=obj.env.cr if isinstance(obj, models.BaseModel) else obj
    cr.execute(sql, para)
    records =cr.fetchall()
    return extract_ids(records)

def obj_to_dict(obj):
    values = {}
    for name,field in obj._fields.items():
        if field.automatic or field.compute:
            continue
        value = getattr(obj, name)            
        if not value:
            continue
        if isinstance(value, models.BaseModel):
            if field.type =='one2many' :
                continue
            if field.type =='many2many':
                value = [(6,0, value.ids)]
            else:
                value = value.id
        values[name]=value
        
    return values
        
        

def truncate_day(datetime):
    ''' Sugar for :py:func:`truncate(datetime, 'day')` '''
    return truncate(datetime, 'day')


def truncate_week(datetime):
    '''
    Truncates a date to the first day of an ISO 8601 week, i.e. monday.

    :params datetime: an initialized datetime object
    :return: `datetime` with the original day set to monday
    :rtype: :py:mod:`datetime` datetime object
    '''
    return datetime - timedelta(days=datetime.isoweekday() - 1)


def truncate_month(datetime):
    ''' Sugar for :py:func:`truncate(datetime, 'month')` '''
    return truncate(datetime, 'month')


def truncate_quarter(datetime):
    '''
    Truncates the datetime to the first day of the quarter for this date.

    :params datetime: an initialized datetime object
    :return: `datetime` with the month set to the first month of this quarter
    :rtype: :py:mod:`datetime` datetime object
    '''
    month = datetime.month
    if month >= 1 and month <= 3:
        return datetime.replace(month=1, day=1)
    elif month >= 4 and month <= 6:
        return datetime.replace(month=4, day=1)
    elif month >= 7 and month <= 9:
        return datetime.replace(month=7, day=1)
    elif month >= 10 and month <= 12:
        return datetime.replace(month=10, day=1)


def truncate_half_year(datetime):
    '''
    Truncates the datetime to the first day of the half year for this date.

    :params datetime: an initialized datetime object
    :return: `datetime` with the month set to the first month of this half year
    :rtype: :py:mod:`datetime` datetime object
    '''
    month = datetime.month

    if month >= 1 and month <= 6:
        return datetime.replace(month=1, day=1)
    elif month >= 7 and month <= 12:
        return datetime.replace(month=7, day=1)


def truncate_year(datetime):
    ''' Sugar for :py:func:`truncate(datetime, 'year')` '''
    return truncate(datetime, 'year')


def truncate(datetime, truncate_to='day'):
    '''
    Truncates a datetime to have the values with higher precision than
    the one set as `truncate_to` as zero (or one for day and month).

    Possible values for `truncate_to`:

    * second
    * minute
    * hour
    * day
    * week (iso week i.e. to monday)
    * month
    * quarter
    * half_year
    * year

    Examples::

       >>> truncate(datetime(2012, 12, 12, 12), 'day')
       datetime(2012, 12, 12)
       >>> truncate(datetime(2012, 12, 14, 12, 15), 'quarter')
       datetime(2012, 10, 1)
       >>> truncate(datetime(2012, 3, 1), 'week')
       datetime(2012, 2, 27)

    :params datetime: an initialized datetime object
    :params truncate_to: The highest precision to keep its original data.
    :return: datetime with `truncated_to` as the highest level of precision
    :rtype: :py:mod:`datetime` datetime object
    '''
    if truncate_to in PERIODS:
        return datetime.replace(**PERIODS[truncate_to])
    elif truncate_to in ODD_PERIODS:
        if truncate_to == 'week':
            return truncate(truncate_week(datetime), 'day')
        elif truncate_to == 'quarter':
            return truncate(truncate_quarter(datetime), 'month')
        elif truncate_to == 'half_year':
            return truncate(truncate_half_year(datetime), 'month')
    else:
        raise ValueError('truncate_to not valid. Valid periods: {}'.format(
            ', '.join(PERIODS.keys() + ODD_PERIODS)
        ))
