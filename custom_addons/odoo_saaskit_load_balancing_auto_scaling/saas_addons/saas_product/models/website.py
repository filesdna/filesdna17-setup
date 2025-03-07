from odoo import api, models, fields
from odoo import _, _lt


class Website(models.Model):
    _inherit = 'website'



    def _get_checkout_steps(self, current_step=None):
        """ Return an ordered list of steps according to the current template rendered.

        If current_step is provided, returns only the corresponding step.

        Note: self.ensure_one()

        :param str current_step: The xmlid of the current step, defaults to None.
        :rtype: list
        :return: A list with the following structure:
            [
                [xmlid],
                {
                    'name': str,
                    'current_href': str,
                    'main_button': str,
                    'main_button_href': str,
                    'back_button': str,
                    'back_button_href': str
                }
            ]
        """
        self.ensure_one()
        is_extra_step_active = self.viewref('website_sale.extra_info').active
        redirect_to_sign_in = self.account_on_checkout == 'mandatory' and self.is_public_user()

        partner_id = self.env.user.partner_id
        print("----------------user_id---", partner_id)

        steps = [(['website_sale.cart'], {
            'name': _lt("Review Order"),
            'current_href': '/shop/cart',
            'main_button': _lt("Sign In") if redirect_to_sign_in else _lt("Checkout"),
            'main_button_href': f'{"/web/login?redirect=" if redirect_to_sign_in else ""}/shop/address?partner_id=%s' % partner_id.id,
            'back_button': _lt("Continue shopping"),
            'back_button_href': '/shop',
        }), (['website_sale.checkout', 'website_sale.address'], {
            'name': _lt("Shipping"),
            'current_href': '/shop/checkout',
            'main_button': _lt("Confirm"),
            'main_button_href': f'{"/shop/extra_info" if is_extra_step_active else "/shop/confirm_order"}',
            'back_button': _lt("Back to cart"),
            'back_button_href': '/shop/cart',
        })]
        if is_extra_step_active:
            steps.append((['website_sale.extra_info'], {
                'name': _lt("Extra Info"),
                'current_href': '/shop/extra_info',
                'main_button': _lt("Continue checkout"),
                'main_button_href': '/shop/confirm_order',
                'back_button': _lt("Return to shipping"),
                'back_button_href': '/shop/checkout',
            }))
        steps.append((['website_sale.payment'], {
            'name': _lt("Payment"),
            'current_href': '/shop/payment',
            'back_button': _lt("Back to cart"),
            'back_button_href': '/shop/cart',
        }))

        print("----------------------steps-----", steps)

        if current_step:
            return next(step for step in steps if current_step in step[0])[1]
        else:
            return steps