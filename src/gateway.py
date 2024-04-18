import network
import time
import urequests
from machine import Pin, I2C
import usocket as socket
from umqtt.simple import MQTTClient
from umqtt.simple import MQTTException
import ujson
#import ahtx0

#Credentials and Config
_WIFI_SSID_ = "LPWAN-IoT-06"
_WIFI_PASS_ = "LPWAN-IoT-06-WiFi"

_REMOTE_SERVER_IP_ = "147.229.146.40"
_REMOTE_SERVER_PORT_ = 11883

_CLIENT_ID_ = "06"
_ACCESS_TOKEN_ = ""
_PASSWORD_ = ""
_QOS_=0


tempHigh = 27.0
tempLow = 26.0


mqtterrortable=["Connection Accepted", "Connection Refused, Unacceptable Protocol Version","Connection Refused, Identifier Rejected","Connection Refused, Server Unavailable", "Connection Refused, Bad Username or Password", "Connection Refused, Not Authorized"]

#Initialize MQTT Client
keepalive_seconds = 60 #seconds
client = MQTTClient(_CLIENT_ID_,_REMOTE_SERVER_IP_, user=_ACCESS_TOKEN_, password=_PASSWORD_,keepalive=keepalive_seconds, port=_REMOTE_SERVER_PORT_)

time.sleep(5)

#Connect to Wifi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
print(wlan.scan())
wlan.connect(_WIFI_SSID_,_WIFI_PASS_)

#Initialize sensor
#i2c1 = I2C(1, scl = Pin(3), sda = Pin(2), freq = 400000)
#tmp_sensor = ahtx0.AHT20(i2c1)
#tmp_sensor.initialize()

isReady = False
while ( not isReady):
    print("WIFI STATUS CONNECTED: " + str(wlan.isconnected()))

    if(wlan.isconnected()):
        isReady = True

    time.sleep_ms(500)

print(wlan.ifconfig())

recievedTemp = False
recievedButton = False
tempValue = 0


#MQTT------------------------------------------
#Setup on_message callback function
def on_message_callback(topic, msg):
    print((topic, msg))
    #js = ujson.loads(msg)
    #print(js)
    global recievedTemp
    global recievedButton
    global tempValue

    if (topic == b'IoTProject/2/button/1'):
        recievedButton = True
        print("BUTTON - RECIVED")
    if (topic == b'IoTProject/2/temperature'):
        recievedTemp = True
        tempValue = float(msg)
        print("MSG(temp) = ", tempValue)


#Mount callback
client.set_callback(on_message_callback)

#Connect to server and subscribe to topic

try:
    client.connect()
    client.subscribe(b"IoTProject/2/button/1")
    client.subscribe(b"IoTProject/2/temperature")


except MQTTException as mqtte:
    print("MQTTException : " + str(mqtte)  + " - " + mqtterrortable[int(str(mqtte))])
except:
    print("Other Error")


mqtt_ctr = 0

print("Entering loop")

lightON = False


while (1):

    try:

        client.check_msg()
        mqtt_ctr = mqtt_ctr+1
        if mqtt_ctr >= (keepalive_seconds-2)/0.1:
            mqtt_ctr = 0
            #Keepalive
            client.ping()

        if (recievedTemp == True):

            if(tempValue < tempLow):
                client.publish(b"IoTProject/2/heating", b"True",qos=_QOS_)
            elif(tempValue > tempHigh):
                client.publish(b"IoTProject/2/heating", b"False",qos=_QOS_)

            recievedTemp = False

        if(recievedButton == True):
            if(lightON == False):
                lightON = True
                print("BUTTON - ON")
                client.publish(b"IoTProject/2/light/1", b"True",qos=_QOS_)

            elif(lightON == True):
                lightON = False
                print("BUTTON - OFF")
                client.publish(b"IoTProject/2/light/1", b"False",qos=_QOS_)

            recievedButton = False



    except Exception as exception:
        print("Error: " + str(exception))
    #time.sleep(2)

time.sleep(3)
client.disconnect()
print("End of program")

