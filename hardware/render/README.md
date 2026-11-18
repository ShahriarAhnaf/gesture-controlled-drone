# Worn assembly render

`two-hands.png` and `left-hand-detail.png` were rendered in Blender 5.2.1 LTS.
`palmpilot-two-hands.blend` is editable and contains both hands and the hub.

The rigid carrier geometry, connector bodies, sockets, passives and hub button
come from KiCad GLB exports at **1:1 metric scale**. `assembly-manifest.json`
records the board hashes, hand asset hashes and the carrier origin transforms.
Changing a PCB invalidates the associated exported GLB and render evidence.

The DevKit and Adafruit breakout envelopes, screws, straps, wrist extensions,
cables, button mount and sensor films are illustrative presentation geometry.
They do not establish mounting fit, usable bend radius, sensor strain relief,
sewing dimensions, comfort or clearance on a particular wearer. The #1070 visual
films use 6.41 mm width and a 77.57 mm path, following the product dimensions;
their placement on the meshes remains a concept, not a manufacturing template.
The motion-board axis orientation must be checked against the actual firmware
calibration during assembly; no successful physical axis test is implied.

Hand meshes: [Immersive Web webxr-input-profiles / generic-hand](https://github.com/immersive-web/webxr-input-profiles/tree/f4992299601614adbfefd398dc8e281556bb7444/packages/assets/profiles/generic-hand),
revision `f4992299601614adbfefd398dc8e281556bb7444`. Both `left.glb` and `right.glb`
were downloaded; the right hand is not a procedural stand-in. They are baked in
isolated Blender scenes before assembly to preserve their skinned geometry.
The files are covered by the package's MIT license, Copyright (c) 2019 Amazon;
see `assets/LICENSE.md`. Skin materials and assembly objects were added here.

To rebuild: run `prepare_hands.py` then `scene.py` with Blender, after generating
the three KiCad GLBs. The script saves the scene with its overview camera before
rendering the overview and a separate close-up.
