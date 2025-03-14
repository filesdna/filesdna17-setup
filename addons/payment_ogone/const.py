# Part of Odoo. See LICENSE file for full copyright and licensing details.

# See https://epayments-support.ingenico.com/en/integration-solutions/integrations/directlink#directlink_integration_guides_request_a_new_order
# See https://epayments-support.ingenico.com/en/integration-solutions/integrations/directlink#directlink_integration_guides_order_response
VALID_KEYS = [
    'AAVADDRESS',
    'AAVCHECK',
    'AAVMAIL',
    'AAVNAME',
    'AAVPHONE',
    'AAVZIP',
    'ACCEPTANCE',
    'ALIAS',
    'AMOUNT',
    'BIC',
    'BIN',
    'BRAND',
    'CARDNO',
    'CCCTY',
    'CN',
    'COLLECTOR_BIC',
    'COLLECTOR_IBAN',
    'COMPLUS',
    'CREATION_STATUS',
    'CREDITDEBIT',
    'CURRENCY',
    'CVCCHECK',
    'DCC_COMMPERCENTAGE',
    'DCC_CONVAMOUNT',
    'DCC_CONVCCY',
    'DCC_EXCHRATE',
    'DCC_EXCHRATESOURCE',
    'DCC_EXCHRATETS',
    'DCC_INDICATOR',
    'DCC_MARGINPERCENTAGE',
    'DCC_VALIDHOURS',
    'DEVICEID',
    'DIGESTCARDNO',
    'ECI',
    'ED',
    'EMAIL',
    'ENCCARDNO',
    'FXAMOUNT',
    'FXCURRENCY',
    'IP',
    'IPCTY',
    'MANDATEID',
    'MOBILEMODE',
    'NBREMAILUSAGE',
    'NBRIPUSAGE',
    'NBRIPUSAGE_ALLTX',
    'NBRUSAGE',
    'NCERROR',
    'ORDERID',
    'PAYID',
    'PAYIDSUB',
    'PAYMENT_REFERENCE',
    'PM',
    'SCO_CATEGORY',
    'SCORING',
    'SEQUENCETYPE',
    'SIGNDATE',
    'STATUS',
    'SUBBRAND',
    'SUBSCRIPTION_ID',
    'TICKET',
    'TRXDATE',
    'VC',
]


# See https://epayments-support.ingenico.com/en/get-started/transaction-status-full/
PAYMENT_STATUS_MAPPING = {
    'pending': (41, 46, 50, 51, 52, 55, 56, 81, 82, 91, 92, 99),  # 46 = 3DS
    'done': (5, 8, 9),
    'cancel': (1,),
    'declined': (2,),
}

# The codes of the payment methods to activate when Ogone is activated.
DEFAULT_PAYMENT_METHODS_CODES = [
    # Primary payment methods.
    'card',
    # Brand payment methods.
    'visa',
    'mastercard',
    'amex',
    'discover',
]

# Mapping of payment method codes to Ogone codes.
PAYMENT_METHODS_MAPPING = {
    'card': 'CreditCard',
    'paylib': 'Paylib',
    'p24': 'Przelewy24',
    'bancontact': 'BCMC',
    'paypal': 'PAYPAL',
    'ideal': 'IDEAL',
    'eps': 'EPS',
    'visa': 'VISA',
    'mastercard': 'MasterCard',
    'jcb': 'JCB',
    'klarna_paynow': 'KLARNA_PAYNOW',
    'klarna_pay_over_time': 'KLARNA_PAYLATER',
    'sofort': 'DirectEbanking',
}
