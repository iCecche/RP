#script to blink onboard led connected to GPIO25 every 0.5s

from machine import Pin
from time import sleep

led = Pin('LED', Pin.OUT)
print('Blinking LED Example')

def main():
    while True:
        led.value(not led.value())
        sleep(0.5)
