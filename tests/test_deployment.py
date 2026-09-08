"""Deployment checks that require neither Docker daemon, ROS nor a GPU."""

import ast
import base64
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest


ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "isaac_sim/assets/lekiwi_soarm"


@pytest.mark.parametrize("bad_input", [None, "tag", "record"])
def test_decord_metadata_repair_is_scoped_and_updates_checksum(tmp_path, bad_input):
    spec = importlib.util.spec_from_file_location("repair_decord", ROOT / "docker/repair-decord-metadata.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    info = tmp_path / "decord-0.6.0.dist-info"
    info.mkdir()
    wheel = info / "WHEEL"
    original = b"Wheel-Version: 1.0\nTag: cp36-cp36m-manylinux2010_x86_64\n"
    if bad_input == "tag":
        original = original.replace(b"cp36", b"cp39")
    wheel.write_bytes(original)
    record = info / "RECORD"
    wheel_entry = f"{info.name}/WHEEL,sha256=old,1\n" if bad_input != "record" else ""
    original_record = "decord/library.so,sha256=keep,123\n" + wheel_entry
    record.write_text(original_record)
    if bad_input:
        with pytest.raises(RuntimeError):
            module.repair(info)
        assert wheel.read_bytes() == original
        assert record.read_text() == original_record
        return
    module.repair(info)
    updated = wheel.read_bytes()
    assert updated == original.replace(b"cp36-cp36m", b"py3-none")
    with record.open(newline="") as stream:
        rows = list(csv.reader(stream))
    assert rows[0] == ["decord/library.so", "sha256=keep", "123"]
    digest = base64.urlsafe_b64encode(hashlib.sha256(updated).digest()).rstrip(b"=").decode()
    assert rows[1] == [f"{info.name}/WHEEL", f"sha256={digest}", str(len(updated))]


def run(*args, **kwargs):
    return subprocess.run(args, text=True, capture_output=True, **kwargs)


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_asset", ROOT / "isaac_sim/validate_asset.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bundle_validates_without_reference_workspace(tmp_path):
    # Reproduce deployment: no src/, ROS install, original CAD, or shell tools.
    relocated = tmp_path / "clone with spaces" / "isaac_sim"
    relocated.mkdir(parents=True)
    shutil.copytree(ASSET, relocated / "assets/lekiwi_soarm")
    shutil.copy2(ROOT / "isaac_sim/validate_asset.py", relocated)
    env = dict(os.environ, PATH="/nonexistent", PYTHONPATH="", PYTHONDONTWRITEBYTECODE="1")
    result = run(sys.executable, str(relocated / "validate_asset.py"), cwd=tmp_path, env=env)
    assert result.returncode == 0, result.stderr
    assert "result=PASS" in result.stdout


@pytest.mark.parametrize("filename", ["../meshes/base/missing.stl", "/tmp/external.stl", "package://robot/mesh.stl"])
def test_validator_rejects_missing_or_nonportable_base_mesh(tmp_path, filename):
    validator = load_validator()
    root = ET.parse(ASSET / "urdf/lekiwi_soarm.urdf")
    root.find(".//link[@name='base_link']/visual/geometry/mesh").set("filename", filename)
    broken = tmp_path / "broken.urdf"
    root.write(broken)
    validator.URDF_PATH = broken
    with pytest.raises(AssertionError, match="mesh"):
        validator.validate_urdf()


def test_urdf_rebuild_matches_shipped_geometry(tmp_path):
    pytest.importorskip("xacro")
    shutil.copytree(ASSET / "source_xacro", tmp_path / "source_xacro")
    result = run(sys.executable, str(ROOT / "isaac_sim/build_urdf.py"), env=dict(
        os.environ, LEKIWI_ASSET_DIR=str(tmp_path), PYTHONDONTWRITEBYTECODE="1"
    ))
    assert result.returncode == 0, result.stderr
    actual = ET.canonicalize(from_file=tmp_path / "urdf/lekiwi_soarm.urdf", strip_text=True)
    expected = ET.canonicalize(from_file=ASSET / "urdf/lekiwi_soarm.urdf", strip_text=True)
    assert actual == expected


def test_runtime_has_no_ros_import_or_extension():
    for path in (ROOT / "isaac_sim").glob("*.py"):
        source = path.read_text()
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        assert not any(name.split(".")[0] in {
            "rclpy", "rospy", "tf2_ros", "nav_msgs", "geometry_msgs", "rosgraph_msgs", "ros_odometry"
        } for name in imports), path
        assert "isaacsim.ros2.bridge" not in source, path


def test_compose_is_portable_and_keeps_data_outside_images(tmp_path):
    if shutil.which("docker") is None:
        pytest.skip("Docker CLI is needed to parse Compose (no daemon required)")
    env = dict(os.environ, LEKIWI_DATA_DIR=str(tmp_path / "data with spaces"))
    result = run("bash", str(ROOT / "lekiwi"), "config", "--format", "json", cwd=tmp_path, env=env)
    assert result.returncode == 0, result.stderr
    config = json.loads(result.stdout)
    assert set(config["services"]) == {"sim", "lerobot"}
    assert config["services"]["sim"]["group_add"] == ["1234"]
    for service_name, service in config["services"].items():
        assert service["user"] == f"{os.getuid()}:{os.getgid()}"
        assert service["platform"] == "linux/amd64"
        assert not service.get("privileged", False)
        assert not service.get("devices")
        assert not service.get("ports")
        expected_volumes = [{
            "type": "bind", "source": str(tmp_path / "data with spaces"),
            "target": "/data", "bind": {"create_host_path": False},
        }]
        if service_name == "sim":
            for source, target in (("cache/kit", "cache"), ("isaac-data", "data"), ("logs/sim", "logs")):
                expected_volumes.append({
                    "type": "bind", "source": str(tmp_path / "data with spaces" / source),
                    "target": f"/isaac-sim/kit/{target}", "bind": {"create_host_path": False},
                })
        assert service["volumes"] == expected_volumes
    assert not (tmp_path / "data with spaces").exists()


@pytest.fixture
def fake_docker(tmp_path):
    executable = tmp_path / "bin/docker"
    executable.parent.mkdir()
    # Recording argv verifies quoting and command routing; this never starts a
    # container, contacts a registry, modifies Docker, or accesses hardware.
    executable.write_text(f"#!{sys.executable}\n" + '''
import json, os, sys
args = sys.argv[1:]
with open(os.environ["DOCKER_CALL_LOG"], "a") as stream:
    stream.write(json.dumps(args) + "\\n")
if args[0] == "info" and os.environ.get("DENY_DOCKER"):
    sys.exit(1)
if args[0] == "ps" and os.environ.get("SIM_RUNNING"):
    print("existing-container")
if args[0] == "inspect":
    print(os.environ.get("CONTAINER_OWNER", "lekiwi") + "|" +
          os.environ.get("CONTAINER_CHECKOUT", os.environ["TEST_PROJECT_DIR"]) + "|sim")
if "config" in args and "--images" in args:
    print("lekiwi-" + args[-1] + ":0.1.0")
''')
    executable.chmod(0o755)
    log = tmp_path / "calls.jsonl"
    env = dict(os.environ, PATH=f"{executable.parent}:/usr/bin:/bin",
               DOCKER_CALL_LOG=str(log), LEKIWI_DATA_DIR=str(tmp_path / "data with spaces"),
               TEST_PROJECT_DIR=str(ROOT))
    env.pop("LEKIWI_DOCKER_SUDO", None)
    env.pop("LEKIWI_PROJECT_NAME", None)
    return env, log


def calls(log):
    return [json.loads(line) for line in log.read_text().splitlines()]


def test_denied_docker_does_not_fall_back_to_sudo(fake_docker):
    env, log = fake_docker
    result = run("bash", str(ROOT / "lekiwi"), "setup", env=dict(env, DENY_DOCKER="1"))
    assert result.returncode != 0
    assert "Docker is not accessible" in result.stderr
    assert not any("build" in call for call in calls(log))


@pytest.mark.parametrize("command", ["test-physics", "basic", "test-basic", "test-recording"])
def test_duplicate_simulation_is_rejected_before_launch(fake_docker, command):
    env, log = fake_docker
    result = run("bash", str(ROOT / "lekiwi"), command, env=dict(env, SIM_RUNNING="1"))
    assert result.returncode != 0
    assert "already running" in result.stderr
    assert not any("run" in call or "build" in call for call in calls(log))


def test_stop_refuses_unrelated_container(fake_docker):
    env, log = fake_docker
    result = run("bash", str(ROOT / "lekiwi"), "stop", env=dict(env, CONTAINER_OWNER="another-project"))
    assert result.returncode != 0
    assert not any(call[0] == "stop" for call in calls(log))


def test_stop_refuses_another_checkout_with_same_project_name(fake_docker):
    env, log = fake_docker
    result = run("bash", str(ROOT / "lekiwi"), "stop", env=dict(env, CONTAINER_CHECKOUT="/another/clone"))
    assert result.returncode != 0
    assert not any(call[0] == "stop" for call in calls(log))


def test_stop_targets_only_owned_simulation(fake_docker):
    env, log = fake_docker
    result = run("bash", str(ROOT / "lekiwi"), "stop", env=env)
    assert result.returncode == 0, result.stderr
    assert calls(log)[-1] == ["stop", "--time", "30", "lekiwi-sim"]


def test_training_forwards_arguments_without_shell_expansion(fake_docker):
    env, log = fake_docker
    dataset = "--dataset.root=/data/datasets/a dataset $(must-not-run)"
    result = run("bash", str(ROOT / "lekiwi"), "train", "act", dataset, env=env)
    assert result.returncode == 0, result.stderr
    command = calls(log)[-1]
    assert command[-1] == dataset
    assert "--policy.push_to_hub=false" in command
    assert "--wandb.enable=false" in command
    assert "lerobot-train" in command


@pytest.mark.parametrize("command", ["calibrate", "teleop"])
def test_so101_cannot_skip_questions_from_noninteractive_launcher(fake_docker, command):
    env, log = fake_docker
    result = run("bash", str(ROOT / "lekiwi"), command, "--port", "/dev/ttyACM0", "--id", "test", env=env)
    assert result.returncode != 0
    assert "interactive terminal" in result.stderr
    assert not any("run" in call or "build" in call for call in calls(log))


def test_leader_overlay_only_exposes_selected_serial_device(tmp_path):
    env = dict(os.environ, LEKIWI_LEADER_PORT="/dev/ttyACM42", LEKIWI_LEADER_GID="20",
               LEKIWI_DATA_DIR=str(tmp_path), LEKIWI_UID="12345", LEKIWI_GID="12345")
    result = run("docker", "compose", "-f", str(ROOT / "compose.yaml"), "-f",
                 str(ROOT / "docker/compose.leader.yaml"), "config", "--format", "json", env=env)
    assert result.returncode == 0, result.stderr
    config = json.loads(result.stdout)
    leader = config["services"]["leader"]
    assert leader["network_mode"] == "none"
    assert leader["user"] == "12345:12345"
    assert leader["group_add"] == ["20"]
    assert leader["devices"] == [{"source": "/dev/ttyACM42", "target": "/dev/so101", "permissions": "rw"}]
    assert not leader.get("privileged") and not leader.get("gpus")
    assert not config["services"]["sim"].get("devices")


@pytest.mark.parametrize("name,target", [("test-physics", "physics-test"), ("test-basic", "basic-test"), ("test-recording", "recording-test")])
def test_physics_test_uses_bundled_image_and_scoped_container(fake_docker, name, target):
    env, log = fake_docker
    result = run("bash", str(ROOT / "lekiwi"), name, env=env)
    assert result.returncode == 0, result.stderr
    command = calls(log)[-1]
    assert command[-2:] == ["sim", target]
    assert command[command.index("--name") + 1] == "lekiwi-sim"
    assert "--rm" in command


def test_course_test_routes_to_same_scoped_simulator(fake_docker):
    env, log = fake_docker
    result = run("bash", str(ROOT / "lekiwi"), "test-scene", env=env)
    assert result.returncode == 0, result.stderr
    command = calls(log)[-1]
    assert command[-2:] == ["sim", "course-test"]
    assert command[command.index("--name") + 1] == "lekiwi-sim"


def test_duplicate_course_does_not_open_second_simulator(fake_docker):
    env, log = fake_docker
    result = run("bash", str(ROOT / "lekiwi"), "scene", "--seed", "42", env=dict(env, SIM_RUNNING="1"))
    assert result.returncode != 0 and "already running" in result.stderr
    assert not any("run" in call for call in calls(log))


def test_shipped_usd_dependencies():
    pytest.importorskip("pxr.UsdUtils")
    spec = importlib.util.spec_from_file_location("bundle_dependencies", ROOT / "isaac_sim/bundle_dependencies.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.validate_bundle_dependencies(ASSET / "usd/lekiwi_soarm.usd")


@pytest.mark.parametrize("message,exit_code,expected", [
    ("CHECK result=PASS", 0, 0),
    ("CHECK result=FAIL", 0, 1),
    ("CHECK result=PASS", 2, 2),
    ("", 0, 1),
])
def test_checked_runner_detects_masked_isaac_failure(tmp_path, message, exit_code, expected):
    result = run("bash", str(ROOT / "docker/run-checked.sh"), "CHECK result=PASS",
                 sys.executable, "-c", f"print({message!r}); raise SystemExit({exit_code})",
                 env=dict(os.environ, LEKIWI_LOG_DIR=str(tmp_path)))
    assert result.returncode == expected, result.stderr
