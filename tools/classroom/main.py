"""1~3장 기초 예제·4~5장 키보드 검사·6장 데이터 목록을 여는 로컬 실행기."""
import fcntl
import os
from pathlib import Path
import subprocess
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]

LESSONS = {
    "1장 · 객체와 물리": (("basic", "--chapter", "1"), "01_object_physics"),
    "2장 · 로봇 관절": (("basic", "--chapter", "2"), "02_robot_joints"),
    "3장 · 카메라 API": (("basic", "--chapter", "3"), "03_robot_cameras"),
    "4장 · 텔레옵 (키보드 미리보기)": (("scene",), "04_teleoperation"),
    "5장 · 데이터 취득 (키보드 검사)": (("record",), "05_data_recording"),
    "6장 · 변환·학습·추론 (데이터 목록)": (("dataset", "list"), "06_lekiwi_dataset"),
}


def command(lesson):
    if lesson not in LESSONS:
        raise ValueError("실습을 선택하세요.")
    return [str(ROOT / "lekiwi"), *LESSONS[lesson][0]]


class Session:
    """실행기 자신이 시작한 프로세스와 컨테이너만 관리한다."""
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.process = self.stop_process = None
        self.log = None
        self.env = None
        self.session_dir = None

    @property
    def running(self):
        return self.process is not None and self.process.poll() is None

    def start(self, args):
        if self.running or (self.stop_process and self.stop_process.poll() is None):
            raise RuntimeError("이전 실습의 종료를 기다리세요.")
        folder = self.data_dir / "classroom"
        folder.mkdir(parents=True, exist_ok=True)
        self.session_dir = Path(tempfile.mkdtemp(prefix="session.", dir=folder))
        self.env = dict(os.environ, LEKIWI_CLASSROOM_SESSION=uuid.uuid4().hex,
                        LEKIWI_COURSE_LAYOUT="random", LEKIWI_RECORDING="0",
                        LEKIWI_TELEOP_STATE="", LEKIWI_TELEOP_SESSION="")
        self.log = self.session_dir / "run.log"
        with self.log.open("w") as output:
            self.process = subprocess.Popen(args, cwd=ROOT, env=self.env,
                                            stdin=subprocess.DEVNULL, stdout=output,
                                            stderr=subprocess.STDOUT)
        self.stop_process = None

    def stop(self):
        if not self.running:
            return
        if self.stop_process and self.stop_process.poll() is None:
            return
        with (self.session_dir / "stop.log").open("w") as output:
            self.stop_process = subprocess.Popen([str(ROOT / "lekiwi"), "stop"], cwd=ROOT,
                env=self.env, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)

    def tail(self):
        if self.log is None:
            return ""
        with self.log.open("rb") as stream:
            stream.seek(max(0, self.log.stat().st_size - 18000))
            return stream.read().decode(errors="replace")


def main():
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except ImportError:
        raise SystemExit("실행 창에는 Ubuntu python3-tk가 필요합니다: sudo apt install python3-tk")
    data_dir = Path(os.environ.get("LEKIWI_DATA_DIR", ROOT / "data"))
    if not data_dir.is_absolute():
        raise SystemExit("LEKIWI_DATA_DIR에는 절대 경로를 지정하세요.")
    data_dir.mkdir(parents=True, exist_ok=True)
    lock = (data_dir / ".classroom.lock").open("a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("이 데이터 폴더의 교육 실행기가 이미 열려 있습니다.")
    try:
        window = tk.Tk()
    except tk.TclError:
        raise SystemExit("이 PC의 그래픽 세션 터미널에서 실행하세요.")
    window.title("LeKiwi 교육 실습 실행기")
    window.geometry("850x660")
    panel = ttk.Frame(window, padding=16)
    panel.pack(fill="both", expand=True)
    ttk.Label(panel, text="실습을 선택하고 교재의 실행 순서를 확인하세요.",
              font=("sans", 15, "bold")).pack(anchor="w", pady=8)
    lesson = tk.StringVar(value=next(iter(LESSONS)))
    ttk.Combobox(panel, textvariable=lesson, values=list(LESSONS), state="readonly").pack(fill="x", pady=5)
    ttk.Label(panel, text="4·5장 USB 리더와 6장 변환·학습·추론은 교재의 터미널 명령으로 실행합니다.").pack(anchor="w", pady=8)
    session = Session(data_dir)
    state = tk.StringVar(value="실습을 선택한 뒤 시작하세요.")
    controls = ttk.Frame(panel)
    controls.pack(fill="x", pady=8)

    def start():
        try:
            args = command(lesson.get())
            session.start(args)
            state.set("데이터 목록 조회 중 · 아래 결과를 확인하세요." if args[1] == "dataset"
                      else "시작 중 · 첫 실행은 수 분 걸릴 수 있습니다.")
        except (ValueError, RuntimeError, OSError) as exc:
            messagebox.showerror("실행 실패", str(exc))

    def stop():
        if session.running and messagebox.askokcancel("실습 종료", "저장하지 않은 편집·기록은 사라집니다. 저장을 마쳤다면 종료하세요."):
            session.stop()
            state.set("종료 요청 중 · 컨테이너 종료를 기다립니다.")

    def textbook():
        path = ROOT / "isaacsim_basic" / LESSONS[lesson.get()][1] / "README.md"
        # 설치된 문서 편집기에서 열며 별도 웹 서버를 만들지 않는다.
        subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    start_button = ttk.Button(controls, text="실습 시작", command=start)
    start_button.pack(side="left", padx=4)
    stop_button = ttk.Button(controls, text="실습 종료", command=stop)
    stop_button.pack(side="left", padx=4)
    ttk.Button(controls, text="교재 열기", command=textbook).pack(side="left", padx=4)
    ttk.Label(panel, textvariable=state, wraplength=790).pack(anchor="w", pady=8)
    output = tk.Text(panel, height=18, wrap="word", state="disabled")
    output.pack(fill="both", expand=True)
    markers = ("ISAACSIM_BASIC ready", "LEKIWI_DRIVE result=READY", "BASIC_RECORDING ready")

    def poll():
        busy = session.running
        stopping = session.stop_process is not None and session.stop_process.poll() is None
        start_button.configure(state="disabled" if busy or stopping else "normal")
        stop_button.configure(state="normal" if busy and not stopping else "disabled")
        log = session.tail()
        if session.process is not None:
            if not busy:
                state.set(f"실습 종료 · 종료 코드 {session.process.returncode} · {session.log}")
            elif stopping:
                state.set("종료 중 · 창과 컨테이너 정리를 기다립니다.")
            elif session.stop_process is not None and session.stop_process.returncode != 0:
                state.set("종료 요청 실패 · 아직 시작 중이면 잠시 후 다시 종료하세요. " +
                          str(session.session_dir / "stop.log"))
            elif any(marker in log for marker in markers):
                state.set("실습 실행 준비 완료 · Isaac Sim 창에서 교재를 따라 진행하세요.")
        output.configure(state="normal")
        output.delete("1.0", "end")
        output.insert("end", log)
        output.see("end")
        output.configure(state="disabled")
        window.after(1000, poll)

    def close():
        if session.running or (session.stop_process and session.stop_process.poll() is None):
            messagebox.showinfo("실습 실행 중", "실습을 저장하고 '실습 종료'를 눌러 종료를 확인한 뒤 실행기를 닫으세요.")
            return
        window.destroy()

    window.protocol("WM_DELETE_WINDOW", close)
    poll()
    window.mainloop()
    lock.close()


if __name__ == "__main__":
    main()
