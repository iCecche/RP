# demo battery status checker for lithium 18650 battery 3.7V (max charge 4.2V)
# uso voltage divider per adattare massima tensione in ingresso (4.2V) a massimo valore consentito su GPIO di RB Pico (3.3V)
# sfrutto due resistenze in serie R1 e R2 tale che rapporto R2/R1+R2 sia circa 0.6666... -> tale rapporto consente di ridurre la tensione di ingresso 
# ad un massimo di 2.8V: infatti la tensione su R2 è data da: Vr2 = [R2/(R1+R2)] * Vb dove Vb è la tensione della batteria

from machine import Pin, ADC
from time import sleep

VOLTAGE_DROP_FACTOR = 1.50

def check_battery(battery):
    level = battery.read_u16() * (3.3 / 65535) * VOLTAGE_DROP_FACTOR
    print(level)
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

def main():
    battery = ADC(Pin(28))
    battery_level = medium_battery_level(battery)
    print("battery_level: ", battery_level)
    
main()
