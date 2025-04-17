# -*- coding: utf-8 -*-

from odoo import models, fields, api
import websockets
import asyncio
import json
import base64
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import config


class DmsSign(models.Model):
    _inherit = 'dms.file'

    def action_open_locally(self):
        print('open locally')
        # async def listen():
        #     file_data = self.attachment_ids.datas
        #     file_info = {
        #         "file_id": self.id,
        #     }
        #
        #     db_name = request._cr.dbname
        #     uri = f"wss://{db_name}.filesdna.com/websocketdna"
        #     async with websockets.connect(uri) as websocket:
        #         # Send authentication token first
        #         user = self.env.user
        #         auth_token = self.sudo().env['auth.token'].search([('user_id', '=', user.id)], limit=1).name
        #         await websocket.send(auth_token)
        #
        #         # Wait for server confirmation
        #         auth_response = await websocket.recv()
        #         auth_response = json.loads(auth_response)
        #         if not auth_response.get('authenticated'):
        #             raise UserError('Make sure DNA Drive is running while performing this operation.')
        #
        #         # Send the file information after authentication
        #         message = json.dumps({"open_file": file_info})
        #         await websocket.send(message)
        #         response = await websocket.recv()
        #
        # loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(loop)
        # try:
        #     loop.run_until_complete(listen())
        # finally:
        #     loop.close()
