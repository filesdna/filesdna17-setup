1 - New transaction function -> As the previous create_payment_transaction is not supported in odoo 15 so i have implemented new mobikul private function to create transaction, because in case of core new function there is user error and with_user in not working there.
Refrence for transaction https://github.com/odoo/odoo/blob/a7f7233e0eae8ee101d745a9813cba930fd03dcb/addons/payment/controllers/portal.py#L282
2 - Remove post process fun -> as _post_process function is no longer supported this is now impletmented in set_done which we called in case of transaction done.
