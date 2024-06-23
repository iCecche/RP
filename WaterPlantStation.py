#LAST_UPDATE:
#    - added voltage measure for battery 18650 using voltage-divider circuit (and analog reading)
#    - added default settings and save/modify settings through MQTT message:
#        if new settings are defined through mqtt broker RP saves them in a txt file
#        if RP reboots, RP uses settings defined in the txt file
#    - added custom deepsleep with very low energy consumption (in previous commit)
#    - added implementation for irrigation from dashboard (using mqtt expiring message) and support for modification for station parameter (moisture_limit, pump_active_for...) (in previous commit)
#    - added status led (ON during operations/measurement - OFF on deepsleep); onboard led

from machine import Pin, ADC, reset, RTC
from time import sleep, localtime, time
import network
import sys
import utime
import json
import dht
import ntptime
import os
import uio

#third-part library mqtt
from umqtt.simple  import MQTTClient

VOLTAGE_DROP_FACTOR = 1.519

MOISTURELIMIT = 15
ACTIVATE_PUMP_FOR = 5
MISURATION_INTERVAL = 1 * 60 * 60 * 1000
LAST_IRRIGATION = 0
IRRIGATE_NOW = False
SETTINGS_SAVED = True

OFFSET = 1 * 60 * 60


def connectWifi():
    SSID = "Your SSID"
    PASSWORD = "Your PASSWORD"
    
    max_wait = 20
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    try:
        wlan.connect(SSID,PASSWORD)
        while max_wait > 0:
            if wlan.status() < 0 or wlan.status() >= 3:
                break
            max_wait -= 1
            print('waiting for connection...')
            sleep(1)
        
        if wlan.status() != 3:
            raise RuntimeError('wifi connection failed')
        
    except Exception as e:
        writelogs('logfile.txt', "Error: " + str(e))
        raise RuntimeError('wifi connection failed')
    
    if wlan.isconnected() == True:
         
        print("connected")
        status = wlan.ifconfig()
        print('ip = ' + status[0])
        sleep(2)
        
        set_time()

#sets time on the pico via ntp server and manages automatic summer time changes; set RTC with the current time from NTP
def set_time():
    
    ntptime.host = 'pool.ntp.org'  # Using a public NTP server
    try:
        ntptime.settime()  # Set RTC with the current time from NTP
        print("Time set from NTP server.")
    except Exception as e:
        print("Failed to set time from NTP server:", e)
        raise RuntimeError('Failed to set time from NTP server')


    current_time=utime.localtime()
    offset = 1 * 3600  # UTC+1 in seconds
        
    dst_active = (
        (current_time[1] > 3 and current_time[1] < 10) or
        (current_time[1] == 3 and current_time[2] >= 28) or
        (current_time[1] == 10 and current_time[2] < 28)
    )

    if dst_active:
        offset += 3600  # Additional +1 for DST
    
    now=time()
    cet=localtime(now+offset)
    RTC().datetime((cet[0], cet[1], cet[2], cet[6] + 1, cet[3], cet[4], cet[5], 0))
    print("Local time after synchronization：%s" %str(localtime()))
            
def disconnectWifi():
    try:
        wlan = network.WLAN(network.STA_IF)
        wlan.disconnect()
        wlan.active(False)
        wlan.deinit()
    except:
        print("Error disconnecting wifi")
        raise RuntimeError("Error disconnecting wifi")
        

def connectMQTT():
    client = -1
    try:
        client = MQTTClient(client_id=b"YOUR_CLIENT_ID", server=b"YOUR_MQTT_SERVER", port=8883,
                    user=b"YOUR_USER",password=b"YOUR_PASSWORD", keepalive=4000, ssl=True,
                    ssl_params={'server_hostname':'YOUR_MQTT_SERVER'}
        )

        client.set_callback(on_message)
        client.connect()
        sleep(1)
    except:
        print("Error connecting client")
        raise RuntimeError("Error connecting to mqtt client")
    return client

def disconnect(client):
    try:
        client.disconnect()
        sleep(1)
    except:
        print("Error disconnecting client")
        raise RuntimeError("Error disconnecting from mqtt client")
        

def publish(client,topic, payload):
    try:
        print("topic: %s , value: %s" %(topic, payload,))
        client.publish(topic, payload,qos=0,retain=True)
        print("publish Done \n")
        
        writelogs('logfile.txt', 'published')
    except:
        
        print("Error publishing to broker")
        raise RuntimeError("Error publishing to broker")   
    
def subscribe(client,topic):
    print("topic: " + topic)
    client.subscribe(topic)
    print("subscription Done")

#callback used when mqtt recieves a message
def on_message(topic, msg):

    global MOISTURELIMIT, ACTIVATE_PUMP_FOR, MISURATION_INTERVAL, IRRIGATE_NOW, SETTINGS_SAVED

    print("message recieved on topic: ", topic)
    print("message: " + msg.decode())

    decoded_msg = msg.decode()
    
    if (topic == b'new_moisture_limit'):
        if MOISTURELIMIT != int(decoded_msg):
            MOISTURELIMIT = int(decoded_msg)
            SETTINGS_SAVED = False
    elif(topic == b'new_active_pump_for'):
        if ACTIVATE_PUMP_FOR != int(decoded_msg):
            ACTIVATE_PUMP_FOR = int(decoded_msg)
            SETTINGS_SAVED = False
    elif(topic == b'new_misuration_interval'):
        if MISURATION_INTERVAL != int(decoded_msg):
            MISURATION_INTERVAL = int(decoded_msg)
            SETTINGS_SAVED = False
    elif(topic == b'irrigate_now'):
        IRRIGATE_NOW = bool(decoded_msg)
    
#make json format data for mqtt publishing
def makeData(temp, hum, soil_moisture, time_of_misuration, battery_level):
    data = {
        "temperature" : temp,
        "humidity" : hum,
        "soil_moisture": round(soil_moisture,1),
        "soil_moisture_limit": MOISTURELIMIT,
        "irrigation_time": LAST_IRRIGATION,
        "timeOfmisuration": time_of_misuration,
        "misuration_interval": MISURATION_INTERVAL,
        "activate_pump_for": ACTIVATE_PUMP_FOR,
        "battery_level": battery_level
    }
    return data

def ToggleWaterPump(waterPump):
    waterPump.value(1)
    sleep(ACTIVATE_PUMP_FOR)
    waterPump.value(0)

#map value -> from raw adc value to percentage
def mapValue(x, fromMin, fromMax, toMin, toMax):
     return (x - fromMin) * (toMax - toMin) // (fromMax - fromMin) + toMin

def check_battery(battery):
    level = battery.read_u16() * (3.3 / 65535) * VOLTAGE_DROP_FACTOR
    return level

def medium_battery_level(battery):
    records = []
    total = 0
    for i in range(20):
        level = check_battery(battery)
        records.append(level)
        sleep(0.5)
    for value in records:
        total += value
    return total / len(records)

def wakeup():
    for i in range(28):
        if i not in [0, 3, 14, 15, 25, 26]:  # Alcuni GPIO sono usati, come il LED integrato
            gpio = Pin(i, Pin.OUT)
    
    sleep(0.5)
    
    clock_speed = 125000000
    machine.freq(clock_speed)
    
    sleep(0.5)

def gosleep():
    for i in range(28):
        if i not in [25, 14, 15, 0]:  # Alcuni GPIO sono usati, come il LED integrato
            gpio = Pin(i, Pin.IN)
            
    sleep(0.5) 
     
    clock_speed = 48000000
    machine.freq(clock_speed)
    
    sleep(0.5)
    
def delay(seconds):
    seconds = seconds / 60
    for _ in range(seconds):
        sleep(60)

#custom deepsleep implementation
def deepsleep(seconds):

    print("all down before sleep!")
    gosleep()
    sleep(0.1)
    
    print("going to sleep!")

    delay(seconds)

    print("waking up!")
    wakeup()
    sleep(0.1)
    
def wakeupsensors(tempsensor_power, soil_power):
    tempsensor_power.value(1)
    soil_power.value(1)

def gosleepsensors(tempsensor_power, soil_power):
    tempsensor_power.value(0)
    soil_power.value(0)
        
def writelogs(filename, message):
    try:
        file = open(filename, 'a')
        file.write(message + '\n')
        file.close()
    except:
        print("Error writing file")
        raise RuntimeError('Error writing file')

def get_settings():
    global MOISTURELIMIT, ACTIVE_PUMP_FOR, MISURATION_INTERVAL, LAST_IRRIGATION
    file = None
    try:

        # if txt is empty (0 byte) write default settings and use them
        if os.stat("settings.txt")[6] == 0:
            file = open("settings.txt", "w")
            default_setting = {'MOISTURELIMIT': 15, 'ACTIVE_PUMP_FOR': 5, 'MISURATION_INTERVAL': 3600, 'LAST_IRRIGATION': 0}
            file.write(str(default_setting))
            file.close()

        file = open("settings.txt", "r")
        
        # string format use ' instead of " -> replace it to avoid errors with json.load() method
        raw_settings = file.read()
        raw_settings = raw_settings.replace("'", '"')

        # load content in json format
        settings = json.loads(raw_settings)

        # load settings from json data
        MOISTURELIMIT = settings["MOISTURELIMIT"]
        ACTIVE_PUMP_FOR = settings["ACTIVE_PUMP_FOR"]
        MISURATION_INTERVAL = settings["MISURATION_INTERVAL"] 
        LAST_IRRIGATION = settings["LAST_IRRIGATION"]

        file.close()
        file = None
        
    except Exception as e:
        print("error: ", e)
    finally:
        # Ensure the file is closed 
        if file is not None:
            file.close()
            file = None
            print("closing file...")
        print("configured saved settings")

def save_settings():
    global SETTINGS_SAVED
    file = None
    try:
        #clear .txt file
        file = open("settings.txt", "w")
        
        #save actual setting parameters
        settings = {'MOISTURELIMIT': MOISTURELIMIT, 'ACTIVE_PUMP_FOR': ACTIVE_PUMP_FOR, 'MISURATION_INTERVAL': MISURATION_INTERVAL, "LAST_IRRIGATION": LAST_IRRIGATION}

        #write new dictionary in .txt file
        file.write(str(settings))
        SETTINGS_SAVED = True
        
        file.close()
        file = None
    except Exception as e:
        print("error: ", e)
    finally:
        # Ensure the file is closed 
        if file is not None:
            file.close()
            file = None
            print("closing file...")
    
def main():

    #   reset clock speed to 125MHz
    clock_speed = 125000000
    machine.freq(clock_speed)
    
    sleep(0.1)

    global IRRIGATE_NOW, LAST_IRRIGATION, SETTINGS_SAVED
    time_of_misuration = 0
    get_settings()
    
    #   Power supply pin
    tempsensor_power = Pin(2, Pin.OUT)
    soil_power = Pin(22, Pin.OUT)
    
    #   Data pin
    waterPump = Pin(0, Pin.OUT) #relay data pin
    tempsensor = dht.DHT11(Pin(3, Pin.IN)) #digital read value pin
    soil = ADC(Pin(26)) #analog value pin
    battery = ADC(Pin(28))
    
    #   LED pin
    status_led = Pin('LED', Pin.OUT)

    waterPump.value(0)

    while(1):
        try:
            status_led.value(1) #status led on
            connectWifi()
            client = connectMQTT()
             
            subscribe(client,"new_moisture_limit")
            subscribe(client,"new_active_pump_for")
            subscribe(client,"new_misuration_interval")
            subscribe(client,"irrigate_now")
            
            wakeupsensors(tempsensor_power,soil_power)
            sleep(5)

            client.check_msg()
            print("soil limit ", MOISTURELIMIT)
            print("irrigate now: ", IRRIGATE_NOW)

            moisture = soil.read_u16()
            moisture = mapValue(moisture,39500,14000,0,100)
            print("moisture: " + "%.2f" % moisture +"% (adc: "+str(soil.read_u16())+")")
            
           
            battery_level = medium_battery_level(battery)
            print("battery_level: " + "%.2f" % battery_level +"V")
            
            time_of_misuration = "%4d-%02d-%02dT%02d:%02d:%02d" % localtime()[:6] #converte tuple di localtime un una stringa in formato ISO (due cifre per hh,mm,ss es. 2sec -> 02sec)
            print("time_of_misuration:", time_of_misuration)

            if(moisture < MOISTURELIMIT or IRRIGATE_NOW):
                 ToggleWaterPump(waterPump)
                 LAST_IRRIGATION = time_of_misuration
                 print("irrigation_time:", LAST_IRRIGATION)
                 IRRIGATE_NOW = False
                 SETTINGS_SAVED = False
                 
            writelogs('logfile.txt', time_of_misuration)
            data = json.dumps(makeData(0,0,moisture, time_of_misuration, battery_level))
            publish(client,"picoW/sensor",data)
            
            gosleepsensors(tempsensor_power,soil_power)
            disconnect(client)
            disconnectWifi()

        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            disconnectWifi()
            print("Generic error in try block: ", e)
            writelogs('logfile.txt', 'Error: ' + str(e))
            save_settings()
            sleep(5)
            reset()
        
        if(not SETTINGS_SAVED):
            save_settings()
        sleep(1)
        status_led.value(0) #status led off
        print("Going to deep sleep for 1 hour...")   
        deepsleep(3600)
        print("Woke up from deep sleep!")

if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        print("Error: " + str(e))
        save_settings()
        disconnectWifi()
        reset()