# Project library

`PalmPilot.kicad_sym` defines the 3.3 V CH340C mode, TLV1117LV pin mapping and
harness symbols. WCH's pin 4 is typed as power input in its documented 3.3 V
mode; pin numbers, names and geometry are checked against the native symbol.

`PalmPilotModules.pretty/ESP32-S3-WROOM-1.kicad_mod` derives from KiCad 10's
RF_Module footprint. All pads, thermal vias, mask, courtyard, antenna keepout
and STEP model reference are retained. Only off-board antenna silkscreen is
removed to suit the overhang. KiCad libraries are CC BY-SA 4.0 with the library
exception: https://www.kicad.org/libraries/license/

Standard component STEP models resolve through `KICAD10_3DMODEL_DIR` in a
normal KiCad 10 installation. The installed library lacks the Molex 1050170001
STEP model, so the assembly scene labels its USB shell as an envelope proxy.
Its mechanical/mating geometry still requires the manufacturer drawing.
