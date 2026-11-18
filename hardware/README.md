# PalmPilot Rev A — three controller carrier PCBs

Rev A engineering review baseline, 17 November 2026. Based on upstream
`feadf270eef809c407e4ac0974b1099ce042677f`. The upstream firmware is unchanged.

| Project | Size | Circuit |
|---|---|---|
| `left/left-hand.kicad_pro` | 66 × 78 mm | DevKit sockets, five flex inputs, external ENABLE button, IMU harness |
| `right/right-hand.kicad_pro` | 66 × 78 mm | DevKit sockets, five flex inputs, IMU harness; GPIO7 unconnected |
| `hub/hub.kicad_pro` | 54 × 78 mm | DevKit sockets and onboard CALIBRATE button on GPIO7 |

These are two-layer, 1.6 mm carrier boards for genuine Espressif
ESP32-S3-DevKitC-1 v1.1 boards, with 22 positions per socket and 22.86 mm between
rows. They replace the breadboards while retaining the existing MCU modules,
USB power, firmware GPIO assignments and Adafruit #5543 sensor breakouts.
The Freenove board mentioned in upstream bench notes does **not** have this header
geometry. Confirm the physical DevKit before ordering a carrier.

## Connections

Each hand has its own USB supply and communicates with the hub over BLE. The hub
uses a USB **data** cable from the DevKit's **UART-labelled** port to the laptop:
UART0, 115200 baud, JSON lines. GPIO43/44 are not connected on the carrier.
There is no wired connection between the three boards and no battery circuit.

- Flex connectors J4/J5/J6/J7/J8: thumb/index/middle/ring/little. Pin 1 = 3V3;
  pin 2 = ADC. These retain GPIO1/2/4/5/6, respectively. Each input has its own
  47 kR 1% shunt and 100 nF capacitor to ground.
- Hand J2, four-pin JST PH: 1 GND, 2 3V3, 3 SDA, 4 SCL. Use a verified harness to
  Adafruit #5543 VIN/GND/SDA/SCL. This is **not** a directly compatible QT socket.
  The breakout has its own pull-ups; none are added to the carrier.
- LEFT J9: external normally-open ENABLE switch, pin 1 switch signal, pin 2 GND.
  The 10 kR pull-up, 100 nF shunt and 1 kR series circuit retain GPIO7.
- HUB SW1: normally-open 6 mm tactile CALIBRATE button, with the same passive
  network on GPIO7. Upstream's bench firmware profile disables CALIBRATE;
  use the normal hub configuration to exercise the physical input.

Each hand needs one DevKit, one #5543 and five #1070 sensors. The hub needs one
DevKit. BOM CSVs are engineering lists, with exact KiCad footprint names;
passive manufacturer part numbers and assembly-house substitutions are not selected.

## Verification and simulation

KiCad 10.0.3 reports **zero ERC messages, zero DRC violations, zero unconnected
pads and zero footprint/parity errors on all three projects**. Reports and native
physical pad groups are in `build/<project>/`. All tracks follow H/V/45 geometry.
The reports disclose KiCad's default ignored checks; these have not been hidden.
Top copper, bottom copper, silkscreen, native 3D images and schematic PDFs were
visually inspected. Ground is poured on both faces with local shunt returns and
stitching vias. Antennas overhang a carrier notch. Worn RF behavior remains untested.

[The simulation report](simulation/REPORT.md) explains the ngspice results and
remaining limits. In particular, I2C cable capacitance and the ESP32's real raw
ADC fault thresholds need physical measurement. These are review prototypes,
not a fabrication release or proof of flight safety. Gerbers are included for
review; there has been no manufactured-board or wearable-fit test.

## Blender scene

`render/palmpilot-two-hands.blend` contains separate left and right hand meshes,
the actual exported carrier geometry and the hub. `render/two-hands.png` is the
overview; `render/left-hand-detail.png` shows the worn stack more closely.
The DevKit and IMU bodies, straps and wire paths are illustrative proxies.
The [render notes](render/README.md) distinguish these from actual board geometry.

## Next revision

Replace the socketed DevKits with ESP32-S3-WROOM modules soldered directly onto
the hand and hub PCBs. Use the module variant with a built-in PCB antenna, as
selected by the user. Preserve USB power for this revision.
Carry forward the frozen GPIO map, USB host transport requirements and the open
ADC/I2C qualification items documented in the simulation report.

## Rebuild on this Mac

KiCad's bundled Python includes pcbnew, numpy and matplotlib. ngspice 47 and
Blender 5.2.1 LTS were used. From the repository root:

```sh
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
"$KPY" hardware/scripts/generate.py
"$KPY" hardware/scripts/hub.py
"$KPY" hardware/scripts/export.py
"$KPY" hardware/scripts/audit.py
"$KPY" hardware/simulation/run.py
/Applications/Blender.app/Contents/MacOS/Blender -b --python hardware/render/prepare_hands.py
/Applications/Blender.app/Contents/MacOS/Blender -b --python hardware/render/scene.py
```

Exports stop on ERC/DRC/parity failures. Regenerate simulations and renders after
relevant edits; hashes in the evidence bind them to their source revisions.
The complete upstream Simantic firmware suite was not run: the public clone
lacks its private board descriptions and toolchain. No firmware was changed.

## Primary references

- [Upstream wiring and frozen pin map](https://github.com/Samiurr10/gesture-controlled-drone/blob/feadf270eef809c407e4ac0974b1099ce042677f/docs/wiring/README.md)
- [Espressif DevKitC-1 v1.1 guide](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html)
- [Espressif mechanical drawing](https://dl.espressif.com/dl/schematics/esp_idf/DXF_ESP32-S3-DevKitC-1_V1.1_20220429.pdf)
- [Adafruit #5543 guide](https://learn.adafruit.com/adafruit-lsm6ds3tr-c-lis3mdl-precision-9-dof-imu)
- [Adafruit #5543 Eagle source](https://github.com/adafruit/Adafruit-LSM6DS3TR-C-LIS3MDL-PCB)
- [Adafruit #1070 dimensions](https://www.adafruit.com/product/1070)
