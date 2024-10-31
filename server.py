import asyncio
import websockets
import json
import vgamepad as vg
from vgamepad import XUSB_BUTTON
import http.server
import socketserver
import threading
import argparse
import time
from flask import Flask, render_template

app = Flask(__name__)

# Default values
player_count = 4
address = "0.0.0.0"
webport = 8001
socketport = 8000
gamepads=[]
color_mapping = {
    'red': XUSB_BUTTON.XUSB_GAMEPAD_A,
    'blue': XUSB_BUTTON.XUSB_GAMEPAD_B,
    'orange': XUSB_BUTTON.XUSB_GAMEPAD_X,
    'green': XUSB_BUTTON.XUSB_GAMEPAD_Y,
    'yellow': XUSB_BUTTON.XUSB_GAMEPAD_START
}
parser = argparse.ArgumentParser(description='A simple script that Simulates the "Buzz Ps2 controller"')
# Define arguments for variables that users can set from the command line
parser.add_argument('--playercount', type=int, help='The amount of people that want to play')
parser.add_argument('--address', help='The IP-Address that the server will try to host on. (Most likely the IP of this device)')
parser.add_argument('--webport', type=int, help='The port that is used to host the controllers')
parser.add_argument('--socketport', type=int, help='The port that will be used to receive the controller signals')
args = parser.parse_args()

# Update variables if user provided values
if args.playercount is not None:
    player_count = args.playercount

if args.address is not None:
    address = args.address
else:
    print("You did not specify an Address for the server! This script now defaults to 'localhost'. If you want to properly use the server enter a valid IP-Address. \n Type 'python server.py --help' for more information.")

if args.webport is not None:
    webport = args.webport

if args.socketport is not None:
    socketport = args.socketport

@app.route('/')
def index():
    return render_template('index.html') 

def serve_html():
    app.run(debug=False, host='0.0.0.0', port=8001)

server_thread = threading.Thread(target=serve_html)
server_thread.daemon = True
server_thread.start()

print("Web server is running in a separate thread.")

def press_button_based_on_color(color, gamepad, action):
    gamepad.reset()
    global color_mapping

    if color.lower() in color_mapping:
        button = color_mapping[color.lower()]
        if action == "down":
            gamepad.press_button(button)
            gamepad.update()
            time.sleep(0.1)
            gamepad.release_button(button)
            gamepad.update()
            

def create_gamepads(player_count):
    gamepads = []
    for _ in range(player_count):
        gamepad = vg.VX360Gamepad()
        gamepads.append(gamepad)
    return gamepads


connected_clients = set()

async def handler(websocket, path):
    global gamepads
    connected_clients.add(websocket)
    print(f"Client connected: {websocket.remote_address}")
    if (len(gamepads) == 0):
        gamepads = create_gamepads(player_count)

    try:
        async for message in websocket:
            data_str = message
            data = json.loads(data_str)
            color = data.get('color')
            value = data.get('value')
            action = data.get('action')
            thr = threading.Thread(target=press_button_based_on_color, args=(color,gamepads[int(value)-1],action), kwargs={})
            thr.start()
            print('recieved signal with value: '+value+' action:'+action+" color:"+color)

    except websockets.exceptions.ConnectionClosed:
        print(f"Client disconnected: {websocket.remote_address}")
           
    finally:
        # Remove the client from the set 
        connected_clients.remove(websocket)
        if (len(connected_clients) == 0):
            for gamepad in gamepads:
                del gamepad
            
            gamepads=[]

   
start_server = websockets.serve(handler, address, socketport)

asyncio.get_event_loop().run_until_complete(start_server)

asyncio.get_event_loop().run_forever()

