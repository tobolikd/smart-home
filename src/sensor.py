import network
import time
import urequests
from machine import Pin, I2C, Timer
import usocket as socket
from umqtt.simple import MQTTClient
from umqtt.simple import MQTTException
import ujson
import ahtx0

#Credentials and Config
_WIFI_SSID_ = "LPWAN-IoT-07"
_WIFI_PASS_ = "LPWAN-IoT-07-WiFi"

_REMOTE_SERVER_IP_ = "147.229.146.40"
_REMOTE_SERVER_PORT_ = 11883

_CLIENT_ID_ = "CLIENT"
_ACCESS_TOKEN_ = ""
_PASSWORD_ = ""

_KEEPALIVE_SEC_ = 30
_TEMP_SEC_ = 1

### Setup Peripherals ###

heating = Pin(15, Pin.OUT)
light = Pin(16, Pin.OUT)
button = Pin(20, Pin.IN)

heating.value(0)
light.value(0)

i2c1 = I2C(1, scl = Pin(3), sda = Pin(2), freq = 400000)
tmp_sensor = ahtx0.AHT20(i2c1)
tmp_sensor.initialize()

### Connect to wifi ###

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# print(wlan.scan())

for item in wlan.scan():
    if item[0] == _WIFI_SSID_:
        print("SSID found")
        break
else:
    print("SSID not found in scanned networks")
    exit()

wlan.connect(_WIFI_SSID_,_WIFI_PASS_)

time.sleep(5)
while True:
    time.sleep_ms(500)
    print(f"WiFi status: {str(wlan.isconnected())}")
    if(wlan.isconnected()):
        break

print(wlan.ifconfig())


### MQTT topic handlers ###

def handle_heating(msg):
    if (msg == b"True"):
        heating.value(1)
    elif (msg == b"False"):
        heating.value(0)
    else:
        print("ERROR: invalid heating value")

def handle_light(msg):
    if (msg == b"True"):
        light.value(1)
    elif (msg == b"False"):
        light.value(0)
    else:
        print("ERROR: invalid light value")

def on_message_callback(topic, msg):
    print((topic, msg))
    callbacks = {
        b"IoTProject/2/heating": handle_heating,
        b"IoTProject/2/light/1": handle_light,
    }
    fn = callbacks.get(topic)
    if fn:
        fn(msg)
    else:
        print("NOTICE: unknown topic")

### Setup MQTT client ###

mqtterrortable=["Connection Accepted",
                "Connection Refused, Unacceptable Protocol Version",
                "Connection Refused, Identifier Rejected",
                "Connection Refused, Server Unavailable",
                "Connection Refused, Bad Username or Password",
                "Connection Refused, Not Authorized"]

client = MQTTClient(_CLIENT_ID_,_REMOTE_SERVER_IP_, user=_ACCESS_TOKEN_, password=_PASSWORD_,keepalive=_KEEPALIVE_SEC_, port=_REMOTE_SERVER_PORT_)
client.set_callback(on_message_callback)

try:
    client.connect()
    client.subscribe(b"IoTProject/2/heating")
    client.subscribe(b"IoTProject/2/light/1")
except MQTTException as mqtte:
    print(f"MQTTException : {str(mqtte)} - {mqtterrortable[int(str(mqtte))]}")
except Exception as exception:
    print(f"Exception(mqtt init): {exception}")

### Register button callback ###

def button_callback(pin):
    global client
    time.sleep(0.1)
    client.publish(b"IoTProject/2/button/1",str(True))
    print(f"Button Pressed: {str(pin)}")

button.irq(trigger=Pin.IRQ_FALLING, handler=button_callback)

### Periodic procedures ###

def keepalive_update(t):
    try:
        client.ping()
    except Exception as exception:
        print(f"Error(keepalive): {str(exception)}")

def temp_update(t):
    try:
        temp = str(tmp_sensor.temperature)
        client.publish(b"IoTProject/2/temperature",temp)
    except Exception as exception:
        print(f"Error(temp): {str(exception)}")

#Timer(1, mode=Timer.PERIODIC, freq=(keepalive_sec - 2)*1000, callback=keepalive_update)
#Timer(2, mode=Timer.PERIODIC, freq=temp_sec*1000, callback=temp_update)

### Check message loop ###

mqtt_ctr = 0
print("Entering infinite loop")
seconds_counter = 14;
while True:
    try:
        client.check_msg()
        mqtt_ctr = mqtt_ctr+1
        seconds_counter = seconds_counter+1
        if mqtt_ctr >= (_KEEPALIVE_SEC_)/0.1:
            mqtt_ctr = 0
            client.ping()

        #Publish message to topic
        if seconds_counter >= 3/0.1:
            seconds_counter = 0
            temp = str(tmp_sensor.temperature)
            client.publish(b"IoTProject/2/temperature",temp)
    except Exception as exception:
        print(f"Error: {str(exception)}")
    time.sleep(0.1)

client.disconnect()
