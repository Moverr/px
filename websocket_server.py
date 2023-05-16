import asyncio
import json
import secrets

import websockets

JOIN = {}

WATCH = {}

ALL = {}


async def error(websocket, message):
    """
    Send an error message.

    """
    event = {
        "type": "error",
        "message": message,
    }
    await websocket.send(json.dumps(event))

async def the_start(websocket, details):
    """
    Handle a connection from the caller.

    """

    # the set of WebSocket connections
    # receiving moves from this game, and secret access tokens.
    connected = {websocket}

    join_key = secrets.token_urlsafe(12)
    JOIN[join_key] = connected

    watch_key = secrets.token_urlsafe(12)
    WATCH[watch_key] = connected

    stream_id = secrets.token_urlsafe(12)

    leDetails = {'details': details, 'watch_key': watch_key, 'join_key': join_key, 'id': stream_id}

    ALL['stream' + str(len(ALL) + 1)] = leDetails

    print('----->> created watch key:' + watch_key)
    print('----->> Connected:' + str(connected))
    print('----->> Join:' + str(JOIN))
    print('----->> Watch:' + str(WATCH))
    print('----->> ALL:' + str(ALL))

    try:
        # Send the secret access tokens to the browser of the first player,
        # where they'll be used for building "join" and "watch" links.
        event = {
            "status": "go",
            "stream": leDetails
        }
        await websocket.send(json.dumps(event))
        # Receive and process moves from the first player.
        # -------------
        while True:
            data = await websocket.recv()
            # await websocket.send(data)
            websockets.broadcast(connected, json.dumps(json.loads(data)))

    finally:
        del JOIN[join_key]
        del WATCH[watch_key]


async def speak(websocket):
    while True:
        data = await websocket.recv()
        await websocket.send(data)

        print(data)


async def join(websocket, join_key):
    """
    Handle a connection from the second player: join an existing game.

    """
    # Find the Connect Four game.
    try:
        connected = JOIN[join_key]
    except KeyError:
        await error(websocket, "Call not found.")
        return

    # Register to receive audio data from call.
    connected.add(websocket)
    try:
        while True:
            data = await websocket.recv()
            await websocket.send(data)

    finally:
        connected.remove(websocket)


async def watch(websocket, watch_key):
    """
    Handle a connection from a spectator: watch an existing game.

    """

    print('----->> watch key:' + watch_key)

    # Find the Connect Four game.
    try:
        connected = WATCH[watch_key]
    except KeyError:
        await error(websocket, "Call not found.")
        return

    # Register to receive moves from this game.
    connected.add(websocket)
    try:
        await listen(websocket, connected)
        await websocket.wait_closed()
    finally:
        connected.remove(websocket)


async def listen(websocket, connected):
    """
    Receive and process moves from a player.

    """
    async for message in websocket:
        websockets.broadcast(connected, json.dumps(json.loads(message)))


async def available_streams_details(websocket, stream_type):
    """
    Returns a list of running streams depending on type.

    """
    try:
        if stream_type == 'get_all':
            # Return a list of public streams.
            await websocket.send(
                json.dumps({'all': ALL})
            )
    except websockets.ConnectionClosed as e:
        print(f'Terminated----------------------------------->>>>>> ', e)


async def handler(websocket):
    """
    Handle a connection and dispatch it according to who is connecting.

    """
    # Receive and parse the "init" event from the UI.
    message = await websocket.recv()
    event = json.loads(message)

    print("-------event: " + str(event))

    # assert event["type"] == "init"

    if "all" in event:
        # List all the running streams
        await available_streams_details(websocket, event["all"])

    if "join" in event:
        # Second player joins an existing game.
        await join(websocket, event["join"])
    elif "watch" in event:
        # Spectator watches an existing game.
        await watch(websocket, event["watch"])
    elif "start" in event:
        # First player starts a new game.
        await the_start(websocket, event["details"])


class WebSocketServer:

    def __init__(self, host, port, secret):
        self._secret = secret
        self._server = websockets.serve(handler, host, port)

    def start(self):
        asyncio.get_event_loop().run_until_complete(self._server)
        asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    server = WebSocketServer("127.0.0.1", 8002, "fintechexplained", )
    # //WebSocketServer("192.168.139.28", 8002, "fintechexplained", )
    server.start()
