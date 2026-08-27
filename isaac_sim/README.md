# Isaac Sim LeKiwi + SO101

This directory contains the Isaac Sim 5.1 asset and keyboard smoke test for the
modified LeKiwi body with the SO101 follower arm.

## Layout

```text
isaac_sim/
├── assets/lekiwi_soarm/
│   ├── meshes/base/          # copied dumyAssem4 body and omni wheel
│   ├── meshes/soarm/         # copied SO101 meshes
│   ├── source_xacro/         # local ROS geometry copy, reframed for Isaac
│   ├── urdf/                 # generated Isaac-ready URDF
│   └── usd/                  # generated Isaac Sim asset
├── build_urdf.py             # Xacro rendering + Isaac inertial/color overlay
├── build_usd.py              # Isaac URDF import + articulation/drive overlay
├── build_usd.sh              # Docker build launcher
├── validate_asset.py         # URDF, geometry, joint, color validation
├── validate_usd.py           # composed USD validation
├── keyboard_drive.py         # interactive PhysX contact-drive test
├── physics_smoke_test.py     # headless contact-drive regression
├── captures/                 # Isaac-native viewport captures
└── run_keyboard_drive.sh     # Docker GUI launcher
```

The ROS reference package and the original GitHub Isaac project are never
written. Runtime files are copied under `assets/lekiwi_soarm` before use.

## Build and validate

```bash
cd /home/ysj/youn_ws/lekiwi_urdf_after
./isaac_sim/build_usd.sh
./isaac_sim/validate_asset.py
```

`build_usd.sh` uses `nvcr.io/nvidia/isaac-sim:5.1.0` and may request the sudo
password for Docker access. The generated root prim remains `/LeKiwi`.

The read-only assembly fit was originally expressed as:

```text
xyz = -0.008519 -0.018162 0.052884 m
rpy = 0 0 -2.094379865161 rad
```

The Isaac-local `base_link` is redefined so +X points along the SO101 forward
direction. The same physical mount is therefore expressed in the generated
asset as:

```text
xyz = 0.019988279335 0.001703025019 0.052884 m
rpy = 0 0 0 rad
```

Body, collision, wheel, mount, base COM, and base inertia coordinates are all
rotated consistently; the assembled geometry and mass distribution do not
move.

The arm DOF order is `shoulder_pan`, `shoulder_lift`, `elbow_flex`,
`wrist_flex`, `wrist_roll`, `gripper`. Arm visuals use RGBA
`0.55 0.25 0.85 1.0`. Base and wheel grays are carried from the previous Isaac
asset.

## Keyboard smoke test

```bash
cd /home/ysj/youn_ws/lekiwi_urdf_after
./isaac_sim/run_keyboard_drive.sh
```

- `W` / `S`: forward / backward
- `A` / `D`: left / right
- `Q` / `E`: counter-clockwise / clockwise
- `Space`: stop
- `P`: save the active viewport
- `T`: toggle free camera / robot-tracking camera
- Close the Isaac Sim window to exit

The visible wheel remains the original `omni_wheel.stl`. Physics uses 12
invisible passive sphere rollers per wheel, measured from the STL's 12 major
roller components: 40.89530 mm center radius, 9.88918 mm collision radius, and
alternating +/-9.525 mm side offsets. The wheel hub collision is reduced to
43 mm so the roller envelopes, rather than the hub, touch the ground. These 36
rollers are URDF primitive geometry and do not add another mesh file.

The keyboard test advances the PhysX timeline and only commands angular
velocity on `back_wheel_joint`, `left_wheel_joint`, and `right_wheel_joint`.
It does not write or integrate `/LeKiwi`'s pose. Therefore forward, lateral,
and rotational movement come from wheel/roller/ground contact. `W` commands
`base_link +X` directly; there is no keyboard-frame yaw correction. The camera
starts in free mode after its initial placement, so normal viewport mouse
controls are not overwritten. Press `T` only when a chase view is wanted.

For base-only evaluation, the interactive test holds all six SO101 joints at
their URDF home position (`0 rad`) with a runtime-only position drive. The arm
mass, inertia, gravity, and connection to the base remain active; only joint
motion is suppressed. Generated URDF/USD drive values are not overwritten on
disk.

The physical ground has a visual-only 10 cm minor grid and 50 cm major grid.
A yellow line through the spawn origin marks `base_link +X`, which is also the
user-verified arm-forward and `W` direction. The grid curves have no collision
API, so they cannot affect wheel contact or steering.

For a repeatable headless physics regression inside the Isaac Sim container:

```bash
/isaac-sim/python.sh /workspace/physics_smoke_test.py
```

The regression checks idle settling, forward travel, left translation, and
counter-clockwise rotation using the actual `base_link` world transform.

The first GUI launch populates five Docker volumes whose names start with
`lekiwi-isaacsim-`. Later launches reuse them instead of compiling every RTX
shader from scratch. To remove only this project's disposable caches after the
Isaac containers have stopped:

```bash
docker volume rm \
  lekiwi-isaacsim-kit-cache \
  lekiwi-isaacsim-ov-cache \
  lekiwi-isaacsim-pip-cache \
  lekiwi-isaacsim-gl-cache \
  lekiwi-isaacsim-compute-cache
```

## Physics policy

- The base and wheel mass/inertia baseline comes from the existing GitHub Isaac
  USD rather than being replaced by display-only ROS defaults.
- SO101 link inertias and finite limits come from the completed SO101 Xacro.
- Existing Isaac drive gains and articulation solver iterations are carried to
  the generated USD. Arm drive force is bounded to the SO101 URDF effort limit
  of 10 instead of the previous unbounded CAD-import value.
- Collision geometry is imported from explicit URDF collision elements. Visual
  meshes are not automatically duplicated as missing colliders.
- Omni rollers are simplified passive spheres following NVIDIA's bundled Kaya
  URDF strategy. Roller joints have no commanded drive; their contact response
  is solved by PhysX.
- The previous GitHub sensor layer is empty; camera-named prims in that asset
  are visual CAD parts, not active camera sensors.
