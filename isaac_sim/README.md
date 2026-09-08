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
└── run_keyboard_drive.sh     # Docker GUI launcher
```

The ROS reference package and the original GitHub Isaac project are never
written. Runtime files are copied under `assets/lekiwi_soarm` before use.

## Build and validate

```bash
# From the cloned repository root:
ACCEPT_EULA=Y ./lekiwi build-assets
./lekiwi validate
```

`build_usd.sh` forwards to the project Docker launcher. Builds produce a fresh
bundle under `data/asset-build.*`; shipped assets are not overwritten. The
generated root prim remains `/LeKiwi`. Normal users load the bundled USD without
running the build. See the root README for image setup and Docker access.

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
# From the cloned repository root:
ACCEPT_EULA=Y ./lekiwi sim
```

- `W` / `S`: forward / backward
- `A` / `D`: left / right
- `Q` / `E`: counter-clockwise / clockwise
- `1` / `2` / `3`: base speed 1x / 1.5x / 2x (starts at 1x; numpad supported)
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

The demo waits for passive rollers to remain within 0.5 mm and 0.5 mrad for two
consecutive one-second simulation windows before accepting keyboard input.
The runtime has no ROS bridge, topic, TF, or ROS clock dependency. Physical
position is read directly from Isaac and reported in the console.

For base-only evaluation, the interactive test holds the SO101 at its runtime
home pose: wrist roll -90 degrees, all other joints zero by default. This is
clockwise looking from the wrist toward the fingertips. The same offset is
retained during leader teleop. A runtime-only position drive is used. The arm
mass, inertia, gravity, and connection to the base remain active; only joint
motion is suppressed. Generated URDF/USD drive values are not overwritten on
disk.

The physical ground has a visual-only 10 cm minor grid and 50 cm major grid.
A yellow line through the spawn origin marks `base_link +X`, which is also the
user-verified arm-forward and `W` direction. The grid curves have no collision
API, so they cannot affect wheel contact or steering.

For a repeatable headless physics regression inside the Isaac Sim container:

```bash
ACCEPT_EULA=Y ./lekiwi test-physics
```

The regression checks idle settling, forward travel, left translation, and
counter-clockwise rotation using the actual `base_link` world transform.

The Docker launcher stores user configuration and caches under `data/home` and
`data/cache`, with screenshots under `data/captures`. Existing volumes from the
old launcher are not deleted or modified. Containers run with the host user's
UID/GID and load code and assets from the image, not a host workspace mount.

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
