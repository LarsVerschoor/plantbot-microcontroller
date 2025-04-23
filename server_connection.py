import uwebsockets.client
import network
import time
import os
import ujson

class ServerConnection:
    def __init__(self, ws_url, auth_uuid):
        self.ws_url = ws_url
        self.auth_uuid = auth_uuid
        self.websocket = None
        
        self.connect()
        self.authenticate()
    
    def connect(self):
        try:
            self.websocket = uwebsockets.client.connect(self.ws_url)
            print("Connected to websocket {}".format(self.ws_url))
        except Exception as e:
            print("WebSocket connection failed:", e)
    
    def authenticate(self):
        try:
            message = {
                "action": "authenticate",
                "payload": self.auth_uuid
            }
            self.websocket.send(ujson.dumps(message))
        except Exception as e:
            print('Failed to authenticate to server:', e)
    
    def listen(self, callback):
        while True:
            if self.websocket:
                try:
                    message = self.websocket.recv()
                    callback(message)
                except Exception as e:
                    print('Failed to listen', e)
                finally:
                    time.sleep(1)
                

def hello():
    with uwebsockets.client.connect('ws://192.168.1.152/') as websocket:

        uname = os.uname()
        # Create a dictionary with system information
        system_info = {
            "sysname": uname.sysname,
            "release": uname.release,
            "version": uname.version,
            "machine": uname.machine
        }
        
        # Convert the dictionary to a JSON string
        json_data = ujson.dumps(system_info)
        websocket.send(json_data)
        
        while True:
            greeting = websocket.recv()
            print("< {}".format(greeting))
            time.sleep(1)
