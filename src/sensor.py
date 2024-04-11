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

keepalive_sec = 30
temp_sec = 1


mqtterrortable=["Connection Accepted", "Connection Refused, Unacceptable Protocol Version","Connection Refused, Identifier Rejected","Connection Refused, Server Unavailable", "Connection Refused, Bad Username or Password", "Connection Refused, Not Authorized"]

#Setup Peripherals
heating = Pin(15, Pin.OUT)
light = Pin(16, Pin.OUT)
button = Pin(20, Pin.IN)

heating.value(0)
light.value(0)

#Initialize MQTT Client
keepalive_seconds = 60 #seconds
client = MQTTClient(_CLIENT_ID_,_REMOTE_SERVER_IP_, user=_ACCESS_TOKEN_, password=_PASSWORD_,keepalive=keepalive_seconds, port=_REMOTE_SERVER_PORT_)

#Connect to wifi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
print(wlan.scan())
wlan.connect(_WIFI_SSID_,_WIFI_PASS_)

time.sleep(5)

#Setup sensor
i2c1 = I2C(1, scl = Pin(3), sda = Pin(2), freq = 400000)
tmp_sensor = ahtx0.AHT20(i2c1)
tmp_sensor.initialize()

#Check and wait for WiFi connetion.
isReady = False
while ( not isReady):
    print("WIFI STATUS CONNECTED: " + str(wlan.isconnected()))
    
    if(wlan.isconnected()):
        isReady = True
    
    time.sleep_ms(500)

print(wlan.ifconfig())

def pinPressedCallback(pin):
    global client
    time.sleep(0.1)
    client.publish(b"IoTProject/2/button/1",str(True))
    print("Button Pressed: " + str(pin))
    
#Mount IRQs to buttons
button.irq(trigger=Pin.IRQ_FALLING, handler=pinPressedCallback)

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

#Mount callback to client
client.set_callback(on_message_callback)

#Connect to server and subscribe to topics
try:
    client.connect()
    client.subscribe(b"IoTProject/2/heating")
    client.subscribe(b"IoTProject/2/light/1")
except MQTTException as mqtte:
    print("MQTTException : " + str(mqtte)  + " - " + mqtterrortable[int(str(mqtte))])
except:
    print("Other Error")


mqtt_ctr = 0

def keepalive_update(t):
    try:
        client.ping()
    except Exception as exception:
        print("Error(keepalive): " + str(exception))

def temp_update(t):
    try:
        temp = str(tmp_sensor.temperature)
        client.publish(b"IoTProject/2/temperature",temp)
    except Exception as exception:
        print("Error(temp): " + str(exception))

#timer_keepalive = Timer()
#timer_keepalive.init(mode=Timer.PERIODIC, freq=(keepalive_sec - 2)*1000, callback=keepalive_update)

#timer_temp = Timer()
#timer_temp.init(mode=Timer.PERIODIC, freq=temp_sec*1000, callback=temp_update)

print("Entering infinite loop")
seconds_counter = 14;
while True:
    try:
        client.check_msg()
        mqtt_ctr = mqtt_ctr+1
        seconds_counter = seconds_counter+1
        if mqtt_ctr >= (keepalive_seconds-2)/0.1:
            mqtt_ctr = 0
            client.ping()
            
            
        #Publish message to topic
        if seconds_counter >= 3/0.1:
            seconds_counter = 0
            temp = str(tmp_sensor.temperature)
            client.publish(b"IoTProject/2/temperature",temp)
    except Exception as exception:
        print("Error: " + str(exception))
    time.sleep(0.1)

client.disconnect()
print("End of program")