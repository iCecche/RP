#LAST_UPDATE:
#    - added voltage measure for battery 18650 using voltage-divider circuit (and analog reading)
#    - added default settings and save/modify settings through MQTT message:
#        if new settings are defined through mqtt broker RP saves them in a txt file
#        if RP reboots, RP uses settings defined in the txt file
#    - added custom deepsleep with very low energy consumption (in previous commit)
#    - added implementation for irrigation from dashboard (using mqtt expiring message) and support for modification for station parameter (moisture_limit, pump_active_for...) (in previous commit)
#    - added status led (ON during operations/measurement - OFF on deepsleep); onboard led
#    - use an external secrets.py file to store wifi and mqtt credentials

from machine import Pin, ADC, reset
from time import sleep
import secrets
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

VOLTAGE_DROP_FACTOR = 2.2

SETTINGS_FILE = "settings.txt"
SETTINGS_SAVED = True
SETTINGS = {
    "MOISTURE_LIMIT": 15,
    "ACTIVE_PUMP_FOR": 5,
    "MISURATION_INTERVAL": 3600,
    "LAST_IRRIGATION": 0
}
IRRIGATE_NOW = False

def connectWifi():
    station = network.WLAN(network.STA_IF)
    station.active(True)

    if not station.isconnected():
        print("Connecting...")
        station.connect(secrets.SSID, secrets.PASSWORD)

        while not station.isconnected():
            print(".", end="")
            sleep(1)

    if station.isconnected():
        print("Connected!")
        print("My IP Address:", station.ifconfig()[0])
    else:
        print("Failed to connect to wifi")
        raise RuntimeError('Failed to connect to wifi')

    sleep(1)
    set_time()

# sets time on the pico via ntp server and manages automatic summer time changes; set RTC with the current time from NTP
def set_time():
    ntptime.host = 'pool.ntp.org'

    try:
        ntptime.settime()  # Sets UTC
        print("Time set from NTP server (UTC).")
    except Exception as e:
        print("Failed to set time from NTP server:", e)
        raise RuntimeError('Failed to set time from NTP server')

    print(get_iso_time())

def get_localtime():
    # Get UTC time
    now = utime.time()
    utc = utime.localtime(now)

    # Base offset for CET
    offset = 1 * 3600  # UTC+1

    # DST rule: last Sunday of March until last Sunday of October
    year, month, mday, hour, minute, second, weekday, yearday = utc

    # DST active if:
    # - after last Sunday of March
    # - before last Sunday of October
    # Simplified check:
    if (month > 3 and month < 10) or \
            (month == 3 and mday - weekday >= 25) or \
            (month == 10 and mday - weekday < 25):
        offset += 3600  # Add 1h for summer time (CEST)

    # Apply offset
    cet = utime.localtime(now + offset)
    return cet

def get_iso_time():
    """Return local time as ISO string YYYY-MM-DDTHH:MM:SS."""
    t = get_localtime()
    return "%04d-%02d-%02dT%02d:%02d:%02d" % t[:6]


def disconnectWifi():
    try:
        station = network.WLAN(network.STA_IF)
        if station.isconnected():
            station.disconnect()
        station.active(False)
    except:
        print("Error disconnecting wifi")
        raise RuntimeError("Error disconnecting wifi")


def connectMQTT():
    client = -1
    try:
        client = MQTTClient(client_id=secrets.MQTT_CLIENT, server=secrets.MQTT_SERVER, port=8883,
                            user=secrets.MQTT_USERNAME, password=secrets.MQTT_PASSWORD, keepalive=4000, ssl=True,
                            ssl_params={'server_hostname': secrets.MQTT_SERVER}
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
    global SETTINGS, SETTINGS_SAVED, IRRIGATE_NOW

    print("message recieved on topic: ", topic)
    print("message: " + msg.decode())

    decoded_msg = msg.decode()

    if topic == b'new_moisture_limit':
        if SETTINGS["MOISTURE_LIMIT"] != int(decoded_msg):
            SETTINGS["MOISTURE_LIMIT"] = int(decoded_msg)
            SETTINGS_SAVED = False
    elif topic == b'new_active_pump_for':
        if SETTINGS["ACTIVE_PUMP_FOR"] != int(decoded_msg):
            SETTINGS["ACTIVE_PUMP_FOR"] = int(decoded_msg)
            SETTINGS_SAVED = False
    elif topic == b'new_misuration_interval':
        if SETTINGS["MISURATION_INTERVAL"] != int(decoded_msg):
            SETTINGS["MISURATION_INTERVAL"] = int(decoded_msg)
            SETTINGS_SAVED = False
    elif topic == b'irrigate_now':
        IRRIGATE_NOW = bool(decoded_msg)

# make json format data for mqtt publishing
def makeData(temp, hum, soil_moisture, time_of_misuration, battery_level):
    data = {
        "temperature": temp,
        "humidity": hum,
        "soil_moisture": round(soil_moisture, 1),
        "soil_moisture_limit": SETTINGS["MOISTURE_LIMIT"],
        "irrigation_time": SETTINGS["LAST_IRRIGATION"],
        "timeOfmisuration": time_of_misuration,
        "misuration_interval": SETTINGS["MISURATION_INTERVAL"],
        "activate_pump_for": SETTINGS["ACTIVE_PUMP_FOR"],
        "battery_level": battery_level
    }
    return data

def activatePump(waterPump):
    waterPump.value(1)
    sleep(SETTINGS["ACTIVE_PUMP_FOR"])
    waterPump.value(0)

# map value -> from raw adc value to percentage
def mapValue(x, fromMin, fromMax, toMin, toMax):
    return (x - fromMin) * (toMax - toMin) // (fromMax - fromMin) + toMin

def check_battery(battery):
    level = battery.read_u16() * (3.3 / 65535) * VOLTAGE_DROP_FACTOR
    return level

def medium_battery_level(battery):
    records = []
    total = 0
    for i in range(10):
        level = check_battery(battery)
        records.append(level)
        sleep(0.1)
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

def wakeupsensors(tempsensor_power, soil_power, waterPump_power):
    tempsensor_power.value(1)
    soil_power.value(1)
    waterPump_power.value(1)

def gosleepsensors(tempsensor_power, soil_power, waterPump_power):
    tempsensor_power.value(0)
    soil_power.value(0)
    waterPump_power.value(0)
        
def writelogs(filename, message):
    try:
        file = open(filename, 'a')
        file.write(message + '\n')
        file.close()
    except:
        print("Error writing file")
        raise RuntimeError('Error writing file')

def get_settings():
    """Load settings from file, create defaults if missing/invalid."""
    global SETTINGS_FILE, SETTINGS
    try:
        # If file does not exist or is empty, write defaults
        if not SETTINGS_FILE in os.listdir() or os.stat(SETTINGS_FILE)[6] == 0:
            save_settings()
            return

        with open(SETTINGS_FILE, "r") as f:
            SETTINGS = json.load(f)
        return

    except Exception as e:
        raise RuntimeError("⚠️ Error loading settings:", e)

def save_settings():
    """Save settings dictionary to file in JSON format."""
    global SETTINGS_FILE, SETTINGS, SETTINGS_SAVED
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(SETTINGS, f)
            SETTINGS_SAVED = True
    except Exception as e:
        raise RuntimeError("⚠️ Error saving settings:", e)

def main():
    global SETTINGS, SETTINGS_SAVED, IRRIGATE_NOW

    #   reset clock speed to 125MHz
    clock_speed = 125000000
    machine.freq(clock_speed)
    
    sleep(0.1)

    get_settings()
    
    #   Power supply pin
    tempsensor_power = Pin(2, Pin.OUT)
    soil_power = Pin(22, Pin.OUT)
    waterPump_power = Pin(4, Pin.OUT)
    
    #   Data pin
    waterPump = Pin(0, Pin.OUT) #relay data pin
    tempsensor = dht.DHT22(Pin(3, Pin.IN)) #digital read value pin
    soil = ADC(Pin(26)) #analog value pin
    battery = ADC(Pin(28))
    
    #   LED pin
    status_led = Pin('LED', Pin.OUT)

    waterPump.value(0)

    while(1):
        try:
            status_led.value(1) #status led on
            wakeupsensors(tempsensor_power, soil_power, waterPump_power)
            sleep(1)

            connectWifi()
            client = connectMQTT()

            subscribe(client, "new_moisture_limit")
            subscribe(client, "new_active_pump_for")
            subscribe(client, "new_misuration_interval")
            subscribe(client, "irrigate_now")

            client.check_msg()
            print("soil limit ", SETTINGS["MOISTURE_LIMIT"])
            print("irrigate now: ", SETTINGS["IRRIGATE_NOW"])

            moisture = soil.read_u16()
            moisture = mapValue(moisture, 39500, 14000, 0, 100)
            print("moisture: " + "%.2f" % moisture + "% (adc: " + str(soil.read_u16()) + ")")

            tempsensor.measure()
            temp = tempsensor.temperature()
            hum = tempsensor.humidity()

            battery_level = medium_battery_level(battery)
            print("battery_level: " + "%.2f" % battery_level + "V")

            time_of_misuration = get_iso_time()  # converte tuple di localtime un una stringa in formato ISO (due cifre per hh,mm,ss es. 2sec -> 02sec)
            print("time_of_misuration:", time_of_misuration)

            if moisture < SETTINGS["MOISTURE_LIMIT"] or IRRIGATE_NOW:
                activatePump(waterPump)
                SETTINGS["LAST_IRRIGATION"] = time_of_misuration
                SETTINGS["IRRIGATE_NOW"] = False
                SETTINGS["SETTINGS_SAVED"] = False
                print("irrigation_time:", SETTINGS["LAST_IRRIGATION"])

            data = json.dumps(makeData(temp, hum, moisture, time_of_misuration, battery_level))
            publish(client, "picoW/sensor", data)

            gosleepsensors(tempsensor_power, soil_power, waterPump_power)
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
        
        if not SETTINGS_SAVED:
            save_settings()
        sleep(1)
        status_led.value(0) #status led off
        print("Going to deep sleep for 1 hour...")
        interval_ms = int(SETTINGS["MISURATION_INTERVAL"]) * 1000
        deepsleep(interval_ms)
        print("Woke up from deep sleep!")

if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        print("Error: " + str(e))
        save_settings()
        disconnectWifi()
        reset()