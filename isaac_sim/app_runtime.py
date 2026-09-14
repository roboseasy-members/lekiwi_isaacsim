"""Isaac Sim 5.1의 표준 UI를 로컬 창 또는 WebRTC로 표시합니다."""
import ipaddress
import os
import sys


def install_profiler_defaults():
    """첫 앱에 NVTX 기본값을 적용하고 생성 직전에 원래 SDK 클래스를 복구합니다."""
    import isaacsim
    original = isaacsim.SimulationApp
    # 학생 실행기가 sys.argv를 바꿔도 실행 시 명시한 Kit 옵션은 존중합니다.
    command_args = sys.argv[1:]

    def create(launch_config=None, *args, **kwargs):
        isaacsim.SimulationApp = original
        config = dict(launch_config or {})
        extra = list(config.get("extra_args", []))
        options = command_args + extra

        def provided(key):
            return any(value == key or value.startswith(key + "=") for value in options)

        if not config.get("profiler_backend") and not provided("--/app/profilerBackend"):
            # TSC가 역행하는 CPU에서 Carbonite 206.6 CPU 프로파일러가 종료되는 문제를 피합니다.
            defaults = ["--/app/profilerBackend=nvtx"]
            if not provided("--/app/profileFromStart"):
                defaults.append("--/app/profileFromStart=false")
            config["extra_args"] = defaults + extra
            print("LEKIWI_RUNTIME profiler_backend=nvtx", flush=True)
        return original(config, *args, **kwargs)

    isaacsim.SimulationApp = create


def stream_host(value):
    address = ipaddress.IPv4Address(value)
    if address.is_unspecified or address.is_multicast or int(address) == 0xFFFFFFFF:
        raise ValueError("노트북에서 접속할 데스크탑 IPv4 주소를 지정하세요.")
    return str(address)


def launch_config(config):
    result = dict(config or {})
    mode = os.environ.get("LEKIWI_DISPLAY_MODE", "local")
    if mode not in {"local", "webrtc"}:
        raise ValueError("LEKIWI_DISPLAY_MODE must be local or webrtc")
    if mode == "webrtc":
        stream_host(os.environ.get("LEKIWI_STREAM_HOST", ""))
        result.update(headless=True, hide_ui=False)
        result.setdefault("window_width", result.get("width", 1280))
        result.setdefault("window_height", result.get("height", 720))
    return result


class StreamConnection:
    """접속이 바뀌면 이전 키 입력을 비우고 리더암 추종을 해제합니다."""
    def __init__(self):
        self.connected = False
        self.reset_pending = True
        self.subscriptions = []

    @property
    def input_allowed(self):
        return self.connected and not self.reset_pending

    def set_connected(self, connected):
        self.connected = connected
        self.reset_pending = True
        print(f"LEKIWI_STREAM connected={connected}", flush=True)

    def consume_reset(self):
        reset, self.reset_pending = self.reset_pending, False
        return reset

    def close(self):
        for subscription in self.subscriptions:
            subscription.unsubscribe()
        self.subscriptions.clear()


def enable_streaming(app):
    if os.environ.get("LEKIWI_DISPLAY_MODE", "local") != "webrtc":
        return None
    # 이미 생성된 앱에 중복 서버를 열지 않습니다.
    if hasattr(app, "lekiwi_stream_connection"):
        return app.lekiwi_stream_connection
    from isaacsim.core.utils.extensions import enable_extension
    import omni.kit.app
    import carb.events
    host = stream_host(os.environ.get("LEKIWI_STREAM_HOST", ""))
    for key, value in {
        "/app/window/drawMouse": True,
        "/app/livestream/publicEndpointAddress": host,
        "/app/livestream/port": 49100,
        "/app/livestream/fixedHostPort": 47998,
        "/app/livestream/minHostPort": 47998,
        "/app/livestream/maxHostPort": 47998,
        "/app/livestream/allowResize": True,
    }.items():
        app.set_setting(key, value)
    connection = StreamConnection()
    bus = omni.kit.app.get_app().get_message_bus_event_stream()
    for name, connected in (("client_connected", True), ("client_disconnected", False)):
        kind = carb.events.type_from_string("omni.kit.streamsdk." + name)
        connection.subscriptions.append(bus.create_subscription_to_pop_by_type(
            kind, lambda event, value=connected: connection.set_connected(value)))
    enable_extension("omni.kit.livestream.webrtc")
    manager = omni.kit.app.get_app().get_extension_manager()
    if not manager.is_extension_enabled("omni.kit.livestream.webrtc"):
        connection.close()
        raise RuntimeError("Isaac Sim WebRTC extension failed to start")
    app.lekiwi_stream_connection = connection
    print(f"LEKIWI_STREAM enabled host={host} tcp=49100 udp=47998", flush=True)
    return connection


def install_student_streaming():
    """독립 실행 학생 파일을 바꾸지 않고 첫 SimulationApp 생성만 감쌉니다.

    로컬 실행에서는 아무것도 바꾸지 않습니다. 원격 실행도 생성 직전에 원래
    클래스를 복구하므로 이후 Isaac Sim 확장들의 import에는 영향을 주지 않습니다.
    """
    if os.environ.get("LEKIWI_DISPLAY_MODE", "local") != "webrtc":
        return
    import isaacsim
    original = isaacsim.SimulationApp
    prepare_config = launch_config

    def create(launch_config=None, *args, **kwargs):
        isaacsim.SimulationApp = original
        app = original(prepare_config(launch_config), *args, **kwargs)
        enable_streaming(app)
        return app

    isaacsim.SimulationApp = create
