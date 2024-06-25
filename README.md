# Raspberry Pi Pico Projects and Scripts

Welcome to the Raspberry Pi Pico repository! This repository contains various scripts and projects designed to run on the Raspberry Pi Pico. Whether you're a beginner or an experienced developer, you'll find useful code and examples to get the most out of your Pico.

## Table of Contents

- [About Raspberry Pi Pico](#about-raspberry-pi-pico)
- [Getting Started](#getting-started)
- [Projects](#projects)
  - [Smart Watering Plants RP ](#smart-watering-plants-rp)
- [Scripts](#scripts)
- [Contributing](#contributing)
- [License](#license)

## About Raspberry Pi Pico

The Raspberry Pi Pico is a low-cost, high-performance microcontroller board built around the Raspberry Pi RP2040 chip. With its dual-core ARM Cortex-M0+ processor and flexible I/O options, it's perfect for a wide range of applications, from simple LED blinking to complex IoT systems.

## Getting Started

To get started with the Raspberry Pi Pico, you'll need:

1. A Raspberry Pi Pico board
2. Micro-USB cable
3. A computer with USB ports
4. MicroPython or C/C++ development environment

### Setting Up MicroPython

1. Download and install [Thonny IDE](https://thonny.org/).
2. Connect your Pico to your computer using the micro-USB cable.
3. In Thonny, go to `Tools` > `Options` > `Interpreter` and select `MicroPython (Raspberry Pi Pico)`.

For detailed instructions, refer to the [official Raspberry Pi Pico documentation](https://www.raspberrypi.org/documentation/microcontrollers/raspberry-pi-pico.html).

## Projects

### Smart Watering Plants RP 

This project is a smart watering plant station using MicroPython and a Raspberry Pi Pico. It includes the following features:

- **Battery Voltage Checker**: Monitors the battery level to ensure reliable operation.
- **Soil Moisture Sensor**: Measures soil moisture to determine when watering is needed.
- **Environmental Monitoring**: Measures air temperature and humidity with a DHT22 sensor.
- **MQTT Communication**: Integrates with a Node.js dashboard for remote monitoring and control.
- **5V Pump Control**: Uses a relay to control a 5V water pump for irrigation.
- **Remote Irrigation**: Allows remote control of irrigation via the Node.js dashboard (using MQTT).
- **Custom DeepSleep**: Implements a low energy consumption mode to extend battery life.
- **Settings Management**: Saves default and custom settings in a text file on the Pico, configurable via MQTT.
- **Status LED**: Uses the onboard LED to indicate system status.

## Scripts

This repository also includes various utility scripts for the Raspberry Pi Pico:

- `blink.py`: A simple script to blink an onboard LED.
- `deepsleep.py`: Low energy consumption mode to extend battery life (resolve a RP critical issues)
- `batterystatus.py`: A script to check battery level (voltage) for a 18650 lithium 4.2V battery (using voltage divider circuit).
- `myntptime.py`: A script to set RP time using NTP public server (with winter/summer time support).
- `lcd.py`: LCD Micropyhton library to interface RP with LCD screens.

Each script is well-documented with comments to help you understand how it works and how to modify it for your own purposes.

## Contributing

We welcome contributions! If you have a project or script you'd like to share, please fork the repository and submit a pull request. Make sure to follow the existing code style and include comments in your code.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -m 'Add YourFeature'`)
4. Push to the branch (`git push origin feature/YourFeature`)
5. Open a pull request

## License
