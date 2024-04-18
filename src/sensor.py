import network
import time
import urequests
from machine import Pin, I2C, Timer
import usocket as socket
from umqtt.simple import MQTTClient
from umqtt.simple import MQTTException
import ujson
import ahtx0

def exit():
    while True:
        print("Script has exited")
        time.sleep(5)

# Credentials and Config
WIFI_SSID = b"LPWAN-IoT-06"
WIFI_PASS = b"LPWAN-IoT-06-WiFi"

REMOTE_SERVER_IP = "147.229.146.40"
REMOTE_SERVER_PORT = 11883

CLIENT_ID = "CLIENT"
ACCESS_TOKEN = ""
PASSWORD = ""

KEEPALIVE_SEC = 30
TEMP_SEC = 1

### Constants
TOPIC_PREFIX = b"IoTProject/2/"

TOPIC_HEATING = TOPIC_PREFIX + b"heating"
TOPIC_LIGHT = TOPIC_PREFIX + b"light/"

TOPIC_BUTTON = TOPIC_PREFIX + b"button/"
TOPIC_TEMPERATURE = TOPIC_PREFIX + b"temperature"

TOPICS_SUBSCRIBE = [TOPIC_HEATING, TOPIC_LIGHT + b"#"]

### Setup Peripherals ###

heating = Pin(15, Pin.OUT)
lights = {b"1": Pin(16, Pin.OUT)}
buttons = {Pin(20, Pin.IN): b"1"}

heating.value(0)
for _, light in lights.items():
    light.value(0)

i2c1 = I2C(1, scl=Pin(3), sda=Pin(2), freq=400000)
tmp_sensor = ahtx0.AHT20(i2c1)
tmp_sensor.initialize()

### Connect to wifi ###

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# print(wlan.scan())

for item in wlan.scan():
    if item[0] == WIFI_SSID:
        print("SSID found")
        break
else:
    print("SSID not found in scanned networks")
    exit()

wlan.connect(WIFI_SSID, WIFI_PASS)

time.sleep(5)
while True:
    time.sleep_ms(500)
    print(f"WiFi status: {str(wlan.isconnected())}")
    if wlan.isconnected():
        break

print(wlan.ifconfig())


### MQTT topic handlers ###


def handle_heating(msg, _):
    if msg == b"True":
        heating.value(1)
    elif msg == b"False":
        heating.value(0)
    else:
        print("ERROR: invalid heating value")


def handle_light(msg, suffix):
    light = lights.get(suffix)
    if light == None:
        print("ERROR: invalid light name")
        return

    if msg == b"True":
        light.value(1)
    elif msg == b"False":
        light.value(0)
    else:
        print("ERROR: invalid light value")


def message_callback(topic, msg):
    print((topic, msg))
    callbacks = {
        TOPIC_HEATING: handle_heating,
        TOPIC_LIGHT: handle_light,
    }
    for curr_topic, callback in callbacks.items():
        if topic.startswith(curr_topic):
            callback(msg, topic[len(curr_topic) :])
            break
    else:
        print("NOTICE: unknown topic")


### Setup MQTT client ###

mqtterrortable = [
    "Connection Accepted",
    "Connection Refused, Unacceptable Protocol Version",
    "Connection Refused, Identifier Rejected",
    "Connection Refused, Server Unavailable",
    "Connection Refused, Bad Username or Password",
    "Connection Refused, Not Authorized",
]

client = MQTTClient(
    CLIENT_ID,
    REMOTE_SERVER_IP,
    user=ACCESS_TOKEN,
    password=PASSWORD,
    keepalive=KEEPALIVE_SEC,
    port=REMOTE_SERVER_PORT,
)
client.set_callback(message_callback)

# client.set_last_will("")

try:
    client.connect()
    for topic in TOPICS_SUBSCRIBE:
        client.subscribe(topic)
    # client.subscribe(b"IoTProject/2/heating")
    # client.subscribe(b"IoTProject/2/light/1")
except MQTTException as mqtte:
    print(f"MQTTException : {str(mqtte)} - {mqtterrortable[int(str(mqtte))]}")
except Exception as exception:
    print(f"Exception(mqtt init): {exception}")

### Register button callback ###


def button_callback(pin):
    global client
    time.sleep(0.1)
    print(f"Button Pressed: {str(pin)}")
    name = buttons.get(pin)
    if name == None:
        print(f"Error(bttn): button name not found")
        return

    try:
        client.publish(TOPIC_BUTTON + name, str(True))
    except Exception as exception:
        print(f"Error(bttn): {str(exception)}")


for button in buttons:
    button.irq(trigger=Pin.IRQ_FALLING, handler=button_callback)

### Periodic procedures ###


def keepalive_update(timer):
    print(f"Sending temp")
    try:
        client.ping()
    except Exception as exception:
        print(f"Error(keepalive): {str(exception)}")


def temp_update(timer):
    print(f"Sending temp")
    try:
        temp = str(tmp_sensor.temperature)
        client.publish(TOPIC_TEMPERATURE, temp)
    except Exception as exception:
        print(f"Error(temp): {str(exception)}")


# keepalive_timer = Timer()
# keepalive_timer.init(
#     mode=Timer.PERIODIC, freq=((KEEPALIVE_SEC - 2) * 1000), callback=keepalive_update
# )

# temp_timer = Timer()
# temp_timer.init(mode=Timer.PERIODIC, freq=1000, callback=temp_update)

### Check message loop ###

mqtt_ctr = 0
print("Entering infinite loop")
seconds_counter = 14
while True:
    try:
        client.check_msg()
        mqtt_ctr = mqtt_ctr + 1
        seconds_counter = seconds_counter + 1
        if mqtt_ctr >= (KEEPALIVE_SEC) / 0.1:
            mqtt_ctr = 0
            keepalive_update(0);

        # Publish message to topic
        if seconds_counter >= 3 / 0.1:
            seconds_counter = 0
            temp_update(0)
            # temp = str(tmp_sensor.temperature)
            # client.publish(b"IoTProject/2/temperature", temp)
    except Exception as exception:
        print(f"Error: {str(exception)}")
    time.sleep(0.1)

client.disconnect()

