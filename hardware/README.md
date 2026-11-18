# PalmPilot Rev B — direct ESP32-S3-WROOM module boards

18 November 2026. Replaces the Rev A DevKit carriers at the canonical LEFT,
RIGHT and HUB KiCad paths. Rev A remains in git commit
`d93c8d5c258abfb121f0f205c3fb2d9bdec95d6e`. Rev B is an engineering
review on `hardware/wroom-module-revb`; no boards were ordered.

All three boards are **50 × 58 mm, four copper layers, 1.6 mm nominal**. Each
contains one **ESP32-S3-WROOM-1-N16R8 soldered directly to the PCB**, using its
built-in PCB antenna. There are no DevKit boards or module socket rows.
The 18 × 25.5 mm module overhangs the front edge by 6.25 mm. Its native keepout
contains no host copper. LEFT/RIGHT each retain five flex inputs and an external
Adafruit #5543 motion board. HUB includes its GPIO7 CALIBRATE circuit.

## Integrated support circuit

- TLV1117LV33DCYR ceramic-stable 1 A LDO converts USB 5 V to 3.3 V.
  22 uF / 25 V / X5R 1206 capacitors serve input, output and module bulk;
  local 100 nF capacitors bypass the module and bridge.
- CH340C operates at 3.3 V, with V3 tied to VCC and its internal oscillator.
  ESP GPIO43/TXD0 connects to bridge RXD; bridge TXD connects to GPIO44/RXD0.
  The hub retains UART0 / 115200 baud / JSON USB-to-laptop communication.
  Its R232 mode input is intentionally NC, using the manufacturer's internal pull-down.
- USB Micro-B J1 supplies power and programming/data; USBLC6-2SC6 protects D+/D−.
  The shield is grounded. Native ESP USB GPIO19/20 remain NC.
- EN uses 10 kR / 1 uF and RESET SW1. GPIO0 uses 10 kR and BOOT SW2.
  Hold BOOT, tap RESET, release BOOT to enter the ROM downloader.
  This revision uses manual flashing controls; it has no DTR/RTS auto-reset.
- No battery input or charger is fitted. Each hand uses a USB supply; HUB uses
  a USB data cable to the host. BLE connects the hands to the hub.

## Preserved interfaces and firmware

| Connector | Role | Pins |
|---|---|---|
| J4/J5/J6/J7/J8 | Thumb/index/middle/ring/little flex | 1 = 3V3, 2 = ADC; GPIO1/2/4/5/6 |
| J2, hands only | External #5543 motion harness | 1 GND, 2 3V3, 3 SDA/GPIO8, 4 SCL/GPIO9 |
| J9, LEFT only | Normally-open ENABLE switch | 1 switch, 2 GND; GPIO7 conditioning |
| SW3, HUB only | CALIBRATE | GPIO7 through 10 kR / 100 nF / 1 kR network |

The PH-4 harness is not a QT-compatible cable; verify its mapping. Each flex
input retains 47 kR 1% / 100 nF to ground. The breakout supplies I2C pull-ups;
none are added here. GPIO10, GPIO3/45/46 strapping pins, unused native USB and
module GPIO35/36/37 associated with octal PSRAM remain NC. RIGHT GPIO7 is NC.
The upstream firmware was not modified or rebuilt in this revision. Its existing
8 MB flash image fits the selected 16 MB flash module; PSRAM remains disabled.
A physical boot/flash/USB/BLE/ADC/IMU test is still required, including module
variant and firmware configuration. HUB bench mode disables CALIBRATE.

## Checks and limits

All three saved projects pass KiCad 10.0.3 ERC, DRC with schematic parity, and a
read-only native pad-connectivity audit: **zero reported violations or opens**.
Tracks follow H/V/45 geometry. Reports, board hashes, BOMs, four-layer Gerbers,
drills, layer plots, schematic PDFs and component-bearing GLBs are in `build/`.
All twelve copper Gerber layers were also rendered with PyGerber 2.4.3 at
500 dpi and visually inspected; In1 remains a continuous reference plane.
The project-local WROOM footprint retains the native land pattern, thermal vias,
RF keepout and STEP model; only off-board silkscreen was removed.

In1.Cu is a continuous ground reference; In2.Cu carries 3V3 and a few slow signals
and the USB 5 V feed. Top and bottom have ground pours and stitching. Exact
fabricator stackup, USB differential impedance and signal quality are **not
qualified**. The short full-speed USB route includes a crossover via pair on D+
with nearby return stitching; it is not a length-matched or impedance-certified
USB release. Confirm the Molex connector mechanical drawing and mating clearance
before manufacture; its exact installed-library 3D model is unavailable.

[Simulation results](simulation/REPORT.md) bind to the actual new netlists.
Passive response, EN timing and assumed rail impedance were simulated; the LDO
control loop, radio current waveform, antenna/body interaction, sensor silicon
and raw ADC transfer were not. At 5.25 V / 0.5 A the LDO dissipates about 0.975 W:
actual sustained-load and worn temperatures must be measured. I2C capacitance
and firmware raw fault thresholds remain bench qualifications.

BOMs contain selected module, active-component and capacitor MPNs. Resistor,
connector and switch procurement variants are not frozen; BOMs and Gerbers are
engineering review outputs, not an assembly order or fabrication release.

## Render and rebuilding

`render/palmpilot-two-hands.blend` contains both licensed real hand meshes, the
actual three module-board GLBs, ten sensor films and an illustrative harness.
`render/module-on-hand.png` shows the left module closely;
`render/right-hand-detail.png` and `render/hub-detail.png` show the other two. There is no added
DevKit or module proxy. The missing USB connector shell, external IMU envelopes,
straps, cushions, screws, sensor films and cables are illustrative; this does not
establish wearable fit. See [render notes](render/README.md).

Use KiCad's bundled Python for `scripts/generate.py`, then `scripts/export.py`,
`scripts/audit.py` and `simulation/run.py`. Use Blender for `render/scene.py` after
exporting all three GLBs; `render/details.py` adds the right-hand and hub close-ups.
Native GUI initialization may need an unsandboxed macOS
process. Export fails closed on ERC/DRC violations.

## Manufacturer references

- [Espressif module datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf)
- [Espressif schematic checklist](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html)
- [Espressif layout guidance](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/pcb-layout-design.html)
- [TI TLV1117LV](https://www.ti.com/lit/ds/symlink/tlv1117lv.pdf)
- [WCH CH340 manual](https://www.wch-ic.com/downloads/CH340DS1_PDF.html)
- [ST USBLC6-2](https://www.st.com/resource/en/datasheet/usblc6-2.pdf)
- [Molex USB connector](https://www.molex.com/en-us/products/part-detail/1050170001)
