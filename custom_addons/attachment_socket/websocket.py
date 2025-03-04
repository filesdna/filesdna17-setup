import threading
import asyncio
import websockets
import base64
import json
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry
from odoo.http import request
from odoo.tools import config




connected_clients = {}  # Dictionary to map tokens to connected clients

async def handler(websocket, path):
    try:
        # Step 1: Receive the authentication token
        auth_token = await websocket.recv()

        # Step 2: Validate the authentication token
        if not validate_token(auth_token):
            # Send authentication failure response
            false_auth_meassage = json.dumps({"authenticated":False})
            await websocket.send(false_auth_meassage)
            await websocket.close()
            return
        
        # Send authentication success response
        auth_meassage = json.dumps({"authenticated":True})
        await websocket.send(auth_meassage)
        
        # Step 3: Add the client to the connected clients dictionary with their token
        if auth_token not in connected_clients:
            connected_clients[auth_token] = set()
        connected_clients[auth_token].add(websocket)

        # Step 4: Proceed with handling messages from the authenticated client
        async for message in websocket:
            await process_message(message, auth_token)
    except websockets.ConnectionClosed:
        print("Connection closed")
    finally:
        if auth_token in connected_clients:
            connected_clients[auth_token].remove(websocket)
            if not connected_clients[auth_token]:
                del connected_clients[auth_token]

def validate_token(token):
    db = request.env['ir.config_parameter'].sudo().get_param('web.base.url').split("//")[1].split(".")[0]
    with Registry(db).cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        return env['auth.token'].is_valid_token(token)

async def process_message(message, auth_token):
    data = json.loads(message)
    if "open_file" in data:
        file_info = data["open_file"]
        response = json.dumps({"status": "file_opened", "file_info": file_info})
        await broadcast(response, auth_token)

async def broadcast(message, auth_token):
    if auth_token in connected_clients:
        await asyncio.wait([client.send(message) for client in connected_clients[auth_token]])

def start_websocket_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    start_server = websockets.serve(handler, "0.0.0.0", 8765)
    loop.run_until_complete(start_server)
    loop.run_forever()

websocket_thread = threading.Thread(target=start_websocket_server)
websocket_thread.start()
