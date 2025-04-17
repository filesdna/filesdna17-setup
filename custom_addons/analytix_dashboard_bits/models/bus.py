from odoo import models, fields, api


class CustomBus(models.Model):
    _inherit = 'bus.bus'

    @api.model
    def _sendmany(self, notifications):
        # Custom logic can be added here if needed
        # For example, logging notifications
        for notification in notifications:
            # Log or manipulate notifications if necessary
            pass

        # Call the original method to handle the notifications
        super(CustomBus, self)._sendmany(notifications)