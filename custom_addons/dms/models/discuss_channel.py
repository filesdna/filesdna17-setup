#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    itrack_channel = fields.Boolean('iTrack Channel')

    def _channel_info(self):
        channel_infos = super(DiscussChannel, self)._channel_info()
        channel_infos_dict = dict((c['id'], c) for c in channel_infos)
        for channel in self:
            if channel.itrack_channel:
                channel_infos_dict[channel.id].update({
                    'is_pinned': False,
                })

        return channel_infos