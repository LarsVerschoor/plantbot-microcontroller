import network
import time
import aioble
import bluetooth
import os
import bootsel
import asyncio
from server_connection import ServerConnection

# configure WiFi as a station interface, to connect to a router
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)

# the name of the file in which the wifi credentials are stored
WIFI_CREDENTIALS_FILE = "wifi_credentials.txt"

# the UUID's of the BLE (Bluetooth Low Energy) service and characteristics
WIFI_CREDENTIALS_SERVICE_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef0")
WIFI_SSID_CHAR_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef1")
WIFI_PASSWORD_CHAR_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef2")
CONNECT_UUID_CHAR_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef3")
WIFI_NOTIFICATIONS_CHAR_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef4")

# create the GATT BLE Server and specify operations
configuration_service = aioble.Service(WIFI_CREDENTIALS_SERVICE_UUID)
ssid_characteristic = aioble.Characteristic(configuration_service, WIFI_SSID_CHAR_UUID, read=True, write=True, capture=True)
password_characteristic = aioble.Characteristic(configuration_service, WIFI_PASSWORD_CHAR_UUID, read=True, write=True, capture=True)
connect_uuid_characteristic = aioble.Characteristic(configuration_service, CONNECT_UUID_CHAR_UUID, read=True, write=True, capture=True)
notifications_characteristic = aioble.Characteristic(configuration_service, WIFI_NOTIFICATIONS_CHAR_UUID, notify=True)
aioble.register_services(configuration_service)


# functions to read, write and delete from the WIFI_CREDENTIALS_FILE so the PlantBot can reconnect after a power loss or disconnection
def read_wifi_credentials():
    with open(WIFI_CREDENTIALS_FILE, 'a+') as file: # a+ = append + read, create if not exist, append if exists
        file.seek(0) # set the pointer to the start of the file since it is at the end by default because of append
        lines = file.read().splitlines()
        wifi_ssid = lines[0] if len(lines) > 0 else None
        wifi_password = lines[1] if len(lines) > 1 else None
        return wifi_ssid, wifi_password

def write_wifi_credentials(ssid, password):
    with open(WIFI_CREDENTIALS_FILE, 'w') as file: # w = write, create if not exists, overwrite if exists
        file.write(ssid + '\n' + password)

def delete_wifi_credentials():
    try:
        os.stat(WIFI_CREDENTIALS_FILE)
        os.remove(WIFI_CREDENTIALS_FILE)
    except OSError:
        pass

# function to connect to a router's WiFi network using the SSID and password so it can communicate with the PlantBot server
async def wifi_connect():
    print('connecting to wifi...')
    wifi_ssid, wifi_password = read_wifi_credentials()
    MAX_TRIES = 10
    tries = 0
    if (wifi_ssid == None or wifi_password == None):
        return
    sta_if.connect(wifi_ssid, wifi_password)

    while True:
        if sta_if.isconnected():
            print('connected to wifi')
            return
        tries = tries + 1
        if (tries >= MAX_TRIES):
            return
        await asyncio.sleep(1)

# function to listen for the credentials write to save them in a file so the PlantBot can always reconnect
async def credentials_write(connection):
    conn, encoded_ssid = await ssid_characteristic.written()
    wifi_ssid = encoded_ssid.decode('utf-8')

    conn, encoded_password = await password_characteristic.written()
    wifi_password = encoded_password.decode('utf-8')
    
    conn, encoded_connect_uuid = await connect_uuid_characteristic.written()
    connect_uuid = encoded_connect_uuid.decode('utf-8')
    
    print(wifi_ssid)
    print(wifi_password)
    print(connect_uuid)
    write_wifi_credentials(wifi_ssid, wifi_password)

    notifications_characteristic.notify(connection, b'connecting:starting')
    await wifi_connect()

    if not sta_if.isconnected():
        notifications_characteristic.notify(connection, b'connecting:failed')
        return

    notifications_characteristic.notify(connection, b'connecting:connected')
    
    # blocking other code execution because connection.listen loops forever.
    server = ServerConnection('ws://192.168.1.152/', connect_uuid)
    
    def log_messages(msg):
        print(msg)

    server.listen(log_messages)
    

# function to start BLE advertising and listen for writes
async def peripheral_task():
    while True:
        async with await aioble.advertise(500, name='PlantBot', services=[WIFI_CREDENTIALS_SERVICE_UUID]) as connection:
            print('Connected to a BLE Central')
            await credentials_write(connection)
            await connection.disconnected(timeout_ms=None)


async def main():
    print('starting pico')
    while True:
        time.sleep(1)
        if bootsel.pressed():
            print('bootsel pressed')
            delete_wifi_credentials()
            sta_if.disconnect();
            continue
        if not sta_if.isconnected():
            print('not connected to wifi')
            wifi_ssid, wifi_password = read_wifi_credentials()
            print(wifi_ssid)
            print(wifi_password)
            if (wifi_ssid == None or wifi_password == None):
                await peripheral_task()
                continue
            print('no longer connected to WiFi network. Reconnecting')
            await wifi_connect()
            if (not sta_if.isconnected()):
                print('failed to reconnect to WiFi, trying again in 60 seconds.')
                time.sleep(60)
            continue
        print('connected to wifi')

delete_wifi_credentials()

time.sleep(1)
asyncio.run(main())
