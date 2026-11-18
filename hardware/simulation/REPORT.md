# Schematic simulation before commit

18 November 2026. Rev B direct-module circuits. Status: passive-circuit simulations completed; hardware sign-off
pending. See `results/summary.json` for
source schematic, PCB and exported-netlist SHA-256 hashes.

## What was actually run

ngspice 47 solved the flex divider/shunt capacitor, a timed hard-short/open fault,
power-up, the ENABLE/CALIBRATE network with a bounce stimulus, an I2C RC envelope,
and an assumed ADC charge-removal pulse. Topology and component values were
checked against KiCad-exported XML netlists for **both hands and the hub** before
simulation. The hub and LEFT button networks have identical verified passive
values and connectivity, so the same button deck represents both.

The scope is passive electrical response. No vendor-accurate ESP32 ADC, RF,
LDO control loop, sensor silicon, BSS138 level-shifter or full firmware model is
claimed. The I2C and ADC charge tests are explicitly simplified sensitivities.

## Results and acceptance criteria

| Question and pre-run criterion | Result | Scope |
|---|---|---|
| 25 kR → 100 kR flex step settles to within 1% of its voltage step in ≤20 ms | **PASS: ≤17.79 ms** | Nominal plus 16 corners: rail ±5%, shunt ±1%, cap ±20%, leakage ±50 nA |
| Unplugged node magnitude is <5 mV 50 ms after unplugging | **PASS: ≤2.55 mV** | Same 16 corners; not a guarantee of raw ADC classification |
| Hard short drives the input near its own supply | **PASS: 3.29997 V on 3.3 V** | 0.5 R short model; real ADC saturation still needs measurement |
| Power-up input error is <1 mV 50 ms after the rail ramp ends | **PASS: 0.00224 mV** | 100 kR flex, +1% shunt, +20% capacitor, ideal 1 ms supply ramp |
| Button levels satisfy GPIO low/high limits of 0.25/0.75 × supply | **PASS: 0.3003 V pressed, 3.3000 V released** | 1 R contact assumption; worst calculated pressed level 0.3211 V |
| Standard-mode I2C 30–70% rise ≤1000 ns | **PASS at 100 pF: 889.7 ns; FAIL at 120 pF: 1067.6 ns** | Conservative single 10.5 kR pull-up RC envelope; not the complete breakout model |
| Assumed ADC sampling removes 62 pC without >1 mV node droop | **PASS: 0.776 mV** | Assumed 20 pF × 3.1 V charge, 80 nF shunt; not a vendor ADC simulation |

The nominal flex operating levels are about 2.154 V at 25 kR and 1.055 V at
100 kR. The modeled tolerance envelope is approximately 0.994–2.270 V.
The first sample 10 ms after a step can still have **86.8 mV** of residual error
at the worst corner. A 100 Hz sample rate does not mean each input has settled
fully after a sudden change. The existing RC filter and actual gesture latency
must be evaluated together.

## Findings that remain open

1. **I2C harness:** the conservative RC model allows about 112 pF total host-side
   capacitance with a +5% 10 kR pull-up. This includes cable, pads and pin loads.
   The actual Adafruit board has BSS138 level shifting and pull-ups on both sides;
   their dynamic coupling is omitted. A failing assumed-capacitance corner is not
   proof that the actual assembled bus fails. Measure both SDA and SCL with the
   intended cable before deciding whether a pull-up change is needed. No extra
   pull-up has been silently added.
2. **Open-fault leakage sensitivity:** an assumed +1 uA injection leaves an
   unplugged node near **47.0 mV**. The -1 uA test is an unclamped linear
   sensitivity and reaches about -47 mV. Neither is a vendor ADC leakage model.
   The current firmware uses provisional raw thresholds 40 and 4040. There is no
   validated raw-code transfer model here, so these voltages do not establish
   whether the firmware classifies the fault correctly. Qualify thresholds on
   the real ADC, across supply and sensor/harness conditions, before freezing them.
3. **Debounce:** SPICE shows the analog node crossing thresholds during the chosen
   bounce sequence. The RC network is not a complete debounce system. LEFT uses
   two sampled observations; HUB uses one. Firmware behavior over all sample
   phases and real switch bounce remains a separate test. The upstream bench hub
   profile ignores CALIBRATE entirely.
4. **Power and RF:** the new PCB includes its own TLV1117LV33 regulator and
   module bulk/bypass network. The new rail sweep represents an ideal 3.3 V
   source behind 0.05/0.15/0.30 R and 0.5 uH with 20 uF total effective bulk
   capacitance (10 uF assumed for each nominal 22 uF output/module capacitor)
   and 20 mR ESR. A 30 mA to 500 mA, 1 us load step remains between
   **3.150 and 3.349 V** across these scenarios. This is a source-impedance
   sensitivity, not a vendor LDO model or proof of stability or actual droop.
   Actual MLCC DC-bias derating, regulator loop, cable input droop, peak radio
   current and physical power path require measurement. At 5.25 V input and
   0.5 A, estimated regulator dissipation is **0.975 W**. TI's reference-board
   62.9 C/W value implies about 61 C rise, and is not the thermal resistance
   of this PCB. Sustained-load and worn temperatures remain unqualified.
5. **Module EN:** 10 kR ±1% and 1 uF ±20%, with an ideal 1 ms rail ramp,
   cross 75% of 3.3 V **10.48–16.31 ms after the rail finishes rising**.
   A modeled 10 ms manual reset with a 1 R closed switch holds EN below
   **0.334 mV**, then releases above VIH. This checks passive timing only;
   it does not emulate boot ROM, brownout behavior, switch ESD or firmware.
6. **USB:** netlist checks verify CH340C V3/VCC at 3V3, crossed UART0 TX/RX,
   D+/D−, ESD channels, grounded connector shield and intended NCs. No USB
   signal-integrity, enumeration or ESD-discharge simulation was performed.
   The selected module has built-in PCB antenna; worn RF behavior is unmeasured.

## Numerical checks and retained evidence

The maximum time step was halved from 10 us to 5 us for the flex circuit. The
largest difference at the stated observation times was **0.073 uV**. The nominal
step result differed from the independent first-order RC solution by **0.084 uV**.
These checks support the numerical RC result; they do not validate omitted models.

`results/` retains every generated `.cir` deck, ngspice `.log`, raw `.dat` trace,
corner CSV, summary JSON and a standalone PNG/PDF figure. No simulation failure
was hidden or converted into a physical PASS. KiCad's ERC/DRC reports remain
separate in `../build/<project>/`.

## Sources for limits and models

- [ESP32-S3 datasheet v2.2](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf): GPIO 0.25/0.75 VDD limits. The ±50 nA sweep is a small-leakage scenario; GPIO input figures are not treated as an ADC macro-model.
- [Espressif hardware design guidance](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html): 0.1 uF ADC filtering guidance.
- [NXP UM10204 Rev 7](https://www.nxp.com/docs/en/user-guide/UM10204.pdf): Standard-mode 1000 ns rise-time limit and RC pull-up relation.
- [Adafruit #5543 CAD](https://github.com/adafruit/Adafruit-LSM6DS3TR-C-LIS3MDL-PCB): 10 kR pull-ups, BSS138 translation, default module topology.
- `../../firmware/components/palmpilot_core/hand_core.h`, `board.h` and `../../firmware/apps/hub/main/hub_main.c`: frozen pins, provisional raw thresholds and debounce constants.

Rev B also retains `module_en_*.cir` / `module_rail_*.cir` and `module-power-reset.png`. TI TLV1117LV and WCH CH340 manufacturer references are listed in the hardware README.
