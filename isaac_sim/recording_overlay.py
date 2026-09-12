"""수집 상태를 Viewport 위에 표시합니다. 카메라 Render Product는 변경하지 않습니다."""
from dataclasses import dataclass

from episode_data import FPS


@dataclass(frozen=True)
class RecordingView:
    title: str
    timer: str
    detail: str
    hint: str
    tone: str
    arm: str


def clock_text(frames):
    """벽시계 대신 실제로 접수한 프레임 수를 에피소드 시간으로 표시합니다."""
    tenths = round(max(0, frames) * 10 / FPS)
    minutes, remainder = divmod(tenths, 600)
    seconds, fraction = divmod(remainder, 10)
    return f"{minutes:02d}:{seconds:02d}.{fraction}"


def recording_view(recorder, arm_control=None):
    frames = recorder.writer.count if recorder.writer else 0
    limit = (clock_text(recorder.duration_seconds * FPS)
             if recorder.duration_seconds else "NO LIMIT")
    states = {
        "WARMING UP": ("PREPARING CAMERAS", "Waiting for camera frames", "neutral"),
        "READY": ("READY", "F5  Start recording", "ready"),
        "RECORDING": ("REC  |  RECORDING", "F6  Stop recording", "recording"),
        "FINISHING": ("FINISHING", "Finishing the last frames...", "pending"),
        "UNSAVED": ("STOPPED  |  NOT SAVED", "F7  Save practice   /   F9  Save success", "pending"),
        "SAVING": ("SAVING", "Validating and saving this episode...", "pending"),
        "SAVED": ("SAVED", "F5  Start a new episode", "ready"),
        "DISCARDING": ("DISCARDING", "Discarding the unsaved episode...", "pending"),
        "DISCARDED": ("DISCARDED", "F5  Start a new episode", "neutral"),
        "ERROR": ("RECORDING ERROR", "F10 twice  Discard this take", "recording"),
    }
    title, hint, tone = states.get(recorder.mode, (recorder.mode, "", "neutral"))
    if not recorder.playing and recorder.mode in {"READY", "SAVED", "DISCARDED"}:
        hint = "Press Play before starting a new episode"
    detail = f"{frames:,} frames  |  Episode time (simulation)"
    if recorder.mode == "ERROR":
        detail = recorder.error
    arm = ""
    if arm_control is not None:
        arm = "ARM  Following leader" if arm_control.armed else "ARM  Stopped - R to resume"
    return RecordingView(title, f"{clock_text(frames)}  /  {limit}", detail, hint, tone, arm)


class RecordingOverlay:
    """읽기 전용 화면 표시입니다. 버튼·키 입력·물리 시뮬레이션을 제어하지 않습니다."""
    COLORS = {"recording": 0xFF7070FF, "pending": 0xFF70C8FF,
              "ready": 0xFFA4E28B, "neutral": 0xFFD9D0C8}

    def __init__(self, viewport_window):
        import omni.ui as ui

        self.frame = viewport_window.get_frame("lekiwi.recording.status")
        self.last_view = None
        with self.frame:
            with ui.VStack(opaque_for_mouse_events=False):
                ui.Spacer(height=48)  # 기본 카메라·렌더링 도구 모음을 가리지 않습니다.
                with ui.HStack(height=170, opaque_for_mouse_events=False):
                    ui.Spacer(width=12)
                    with ui.ZStack(width=400, opaque_for_mouse_events=False):
                        ui.Rectangle(style={"background_color": 0xE61C1917, "border_radius": 6},
                                     opaque_for_mouse_events=False)
                        with ui.VStack(opaque_for_mouse_events=False):
                            ui.Spacer(height=10)
                            with ui.HStack(opaque_for_mouse_events=False):
                                ui.Spacer(width=12)
                                with ui.VStack(spacing=4, opaque_for_mouse_events=False):
                                    self.title = ui.Label("", height=24, style={"font_size": 20})
                                    self.timer = ui.Label("", height=34,
                                                          style={"font_size": 30, "color": 0xFFFFFFFF})
                                    self.detail = ui.Label("", height=20, elided_text=True,
                                                           style={"font_size": 15, "color": 0xFFCBC4BE})
                                    self.hint = ui.Label("", height=20,
                                                         style={"font_size": 15, "color": 0xFFF1EAE3})
                                    self.arm = ui.Label("", height=20, style={"font_size": 15})
                                ui.Spacer(width=12)
                            ui.Spacer(height=10)
                    ui.Spacer()
                ui.Spacer()

    def update(self, recorder, arm_control=None):
        view = recording_view(recorder, arm_control)
        if view == self.last_view:
            return  # 표시 내용이 바뀔 때만 갱신하고 화면 구성을 다시 만들지 않습니다.
        self.title.text, self.timer.text = view.title, view.timer
        self.detail.text, self.hint.text, self.arm.text = view.detail, view.hint, view.arm
        self.detail.tooltip = view.detail
        self.title.style = {"font_size": 20, "color": self.COLORS[view.tone]}
        self.arm.style = {"font_size": 15, "color": self.COLORS[
            "ready" if arm_control is not None and arm_control.armed else "pending"]}
        self.last_view = view

    def close(self):
        if self.frame is not None:
            self.frame.clear()  # 이 실행에서 추가한 표시만 제거합니다.
            self.frame = None
