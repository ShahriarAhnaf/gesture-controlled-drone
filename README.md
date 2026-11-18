# PalmPilot

Fly a drone with your hands. Two glove controllers, each an ESP32-S3 with five
flex sensors and a motion sensor, send their readings over Bluetooth to a third
ESP32-S3, the hub. The hub turns finger curl and hand tilt into stick commands for
ArduCopter. The controller is real hardware; the drone is simulated and flies on
screen.

![The simulated quad, flown with the physical gloves and hub](docs/media/flight.gif)

## How it works

```text
left glove  ─┐
             ├─ BLE ─> hub ─ USB ─> laptop ─> ArduCopter ─> motor outputs ─> physics ─> 3D view
right glove ─┘          one command every 20 ms
```

The drone on screen moves only because ArduCopter's motor outputs moved it. No
gesture moves the drone directly.

On the laptop, ArduCopter runs as ArduPilot's native simulator (SITL) in real time.
The same firmware can also run on an emulated STM32F405 flight controller in the
[Simantic](https://simantic.com) simulator, which is how the automated tests fly it.

## Gestures

| Hand | Movement | Drone |
|---|---|---|
| Left | curl four fingers | throttle: open is zero, half curl holds height |
| Left | roll the hand | yaw |
| Right | tilt forward or back | pitch |
| Right | tilt left or right | roll |
| Left | press the button | ENABLE: commands only count while enabled |

Full table, deadbands and safety interlocks: [docs/gesture-mapping.md](docs/gesture-mapping.md).

## Hardware

Three ESP32-S3 DevKits, ten flex sensors and two Adafruit LSM6DS3TR-C + LIS3MDL
motion breakouts, on breadboards for now.

The [Rev B PCB design](hardware/README.md) replaces the DevKits with directly
soldered ESP32-S3-WROOM-1 modules on both hands and the hub. It includes KiCad
schematics, four-layer routing, fabrication review exports, passive simulation
evidence and Blender hand renders. The PCB revision still needs bench
qualification; the breadboard results above do not validate the new boards.

![Left hand wiring](docs/wiring/left-hand.png)

Parts: [docs/bom.md](docs/bom.md). Wiring for each board: [docs/wiring/](docs/wiring/README.md).

## Status

- The whole system works in simulation, from the gloves' firmware to the flying
  drone: both hands and the hub run their real firmware on simulated ESP32-S3s and
  fly ArduCopter on an emulated F405. The latest test run passed 321 of 322 checks.
- The physical controller is built on breadboards and has flown the simulated
  drone. One problem is open: a hand sometimes stops sending while it stays
  connected. Notes: [docs/bench-bringup.md](docs/bench-bringup.md).
- Not done yet: the physical test procedures, a soldered build, and pairing.

## Try it

Build the firmware (ESP-IDF v5.5.2):

```sh
idf.py -C firmware/apps/hand -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.left" build
idf.py -C firmware/apps/hub build
```

Fly the simulated drone with the keyboard, or with a physical hub (needs an
ArduPilot SITL build of Copter-4.7.1 in `tmp/ardupilot` and pymavlink):

```sh
python simulation/drone/demo_view.py --manual             # then open http://localhost:8765
python simulation/drone/demo_view.py --hub /dev/cu.usbserial-XXXX
```

The automated simulation tests (`firmware/tests/`) need the Simantic engine and
board files that are not public yet; [firmware/README.md](firmware/README.md)
describes them.

## How it was tested

Every feature was written and tested in simulation before any sensor was wired.
The simulator runs the exact images that are flashed onto the boards, with test
inputs entering through the simulated chip's own ADC, I2C and GPIO. The same images
then went onto the physical boards.

- [docs/simulation.md](docs/simulation.md): how the simulation runs, the tests, and how the physics was checked
- [docs/test-plan.md](docs/test-plan.md): every test, in order
- [docs/bench-bringup.md](docs/bench-bringup.md): moving to the physical boards, and what simulation could not catch
- [docs/demo.md](docs/demo.md): the laptop demo

## Repository layout

```text
firmware/apps/          hand and hub firmware (and a scripted stand-in hand for tests)
firmware/components/    logic shared by hand and hub: gesture mapping, interlocks, packet format
firmware/tests/         simulation test suites; run_all.sh runs them all
firmware/tools/         build and simulation wrappers; bench/ has tools for the physical boards
simulation/drone/       the bridge to ArduCopter, the physics model, the 3D view
docs/                   design, wiring, tests and notes
hardware/               Rev B module PCBs, electrical evidence and Blender assembly
```

Contributing: [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT ([LICENSE](LICENSE)). `simulation/drone/ardupilot_frame.py` is a port of
ArduPilot code and is GPLv3; [NOTICE](NOTICE) lists it and the other exceptions.
