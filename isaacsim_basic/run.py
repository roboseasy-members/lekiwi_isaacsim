"""Open a fresh, stopped classroom stage inside the existing Isaac Sim image."""
import argparse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--lesson", choices=("blank", "drop", "mass", "friction", "bounce", "basket", "joints", "recording"), default="blank")
args = parser.parse_args()
if args.lesson == "recording":
    from recording import main
    main()
    raise SystemExit(0)

from isaacsim import SimulationApp

app = SimulationApp({"headless": False, "width": 1280, "height": 720})
try:
    import omni.usd
    import omni.timeline
    import omni.kit.app
    from isaacsim.core.utils.extensions import enable_extension
    from isaacsim.core.utils.viewports import set_camera_view
    from scenes import new_exercise

    path = new_exercise("/data/isaacsim_basic", args.lesson)
    context = omni.usd.get_context()
    if not context.open_stage(str(path)):
        raise RuntimeError(f"Cannot open {path}")
    for _ in range(10):
        app.update()
    omni.timeline.get_timeline_interface().stop()
    set_camera_view(eye=(2.4, -3.0, 2.2), target=(0, 0, .35))
    if args.lesson == "joints":
        set_camera_view(eye=(1.05, -1.6, .9), target=(0, 0, .3))
    # Load the stage before installing physics editor listeners. Isaac 5.1
    # crashed in an Sdf callback when opening the first stage immediately
    # after enabling the bundle; loading it after the stage avoids that path.
    # The Python experience only provides computation without these menus.
    enable_extension("omni.physx.bundle")
    manager = omni.kit.app.get_app().get_extension_manager()
    if not manager.is_extension_enabled("omni.physx.bundle"):
        raise RuntimeError("Physics authoring UI could not be enabled")
    for _ in range(10):
        app.update()
    print(f"ISAACSIM_BASIC ready lesson={args.lesson} stage={path}", flush=True)
    print("Press Play to experiment. Save your edits with File > Save. "
          "Course: /opt/lekiwi/isaacsim_basic/README.md", flush=True)
    while app.is_running():
        app.update()
finally:
    app.close()
