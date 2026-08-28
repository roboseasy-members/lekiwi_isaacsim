# Asset provenance

Runtime geometry and Xacro files in this directory were copied from the
read-only package:

```text
/home/ysj/youn_ws/lekiwi_urdf_after/src/lekiwi_soarm_description
```

The body is the `dumyAssem4`-based body exported as
`meshes/base/lekiwi_body_soarm_mount.stl`. The arm mounting transform was fitted
against the read-only `src/0. dumyAssem5.STL` and SolidWorks assembly.

The local Xacro copy is intentionally re-expressed so `base_footprint +X` and
`base_link +X` point along the SO101 arm-forward direction. The original
assembly fit (`xyz=-0.008519 -0.018162 0.052884`,
`rpy=0 0 -2.094379865161`) becomes (`xyz=0.019988279335 0.001703025019
0.052884`, `rpy=0 0 0`) in the new coordinates. Body, wheels, collision, base
COM, and base inertia are transformed by the same basis change, so their
physical assembly is unchanged. The read-only ROS package is not modified.

The existing Isaac physics baseline was inspected from, but not written to:

```text
/home/ysj/youn_ws/isaacsim_prj/lekiwi_isaacsim/urdf/lekiwi/lekiwi.usd
```

The passive omni-roller physics structure was adapted from the Kaya Xacro
bundled in the read-only Isaac Sim 5.1 container:

```text
/isaac-sim/exts/isaacsim.asset.importer.urdf/data/urdf/robots/kaya/urdf/kaya.xacro
```

No Kaya source or mesh was copied. The LeKiwi wheel parameters were measured
from the copied `omni_wheel.stl`: 12 major rollers, 40.89530 mm roller-center
radius, 9.88918 mm simplified sphere radius, and +/-9.525 mm alternating side
offset. These become primitive collision links in the generated URDF/USD while
the original STL remains the only wheel visual mesh.

The ROS-only `base_footprint` is placed on the nominal three-wheel contact plane,
0.075 m below `base_link`. The generated Isaac URDF omits that fixed frame:
Isaac 5.1 otherwise creates it as a zero-mass root rigid body, which makes
direct mobile-base velocity control rotate around the fixed constraint. The
Isaac USD keeps its existing 0.055 m root translation and -0.021 m ground plane,
so this ROS TF correction does not move the assembled geometry or change wheel
contact physics.

Important copied source SHA-256 values:

```text
3bbbeb5d85772893fddff3ad98e97eb0b8fac088afa7baac7f8b26e6e9ed23a2  meshes/base/lekiwi_body_soarm_mount.stl
4c8e0e2b16340d3fd6738ae0077c1363c719b71ed7a54129103dddbd058b3c50  meshes/base/omni_wheel.stl
32da52f2f6432fd3e1aa320993aed81edcd220bb6ce8f6667def2b0cf9978bf5  source_xacro/lekiwi_soarm.urdf.xacro
07b880393f46fff2f00a258112ff0b8520306262a08db0b70dd6233a129323e3  source_xacro/so101/so101_arm_common.xacro
026c32ec178b7ad2512f2f37ed1f73b288dee0aad6f110d800e2843828991c36  source_xacro/so101/end_effectors/so101_ee_common.xacro
cd6e6cc90ee304ed40308d5d75e41b83ddcad40ac86013671060fffb365b9b46  source_xacro/so101/end_effectors/so101_ee_follower.xacro
```
