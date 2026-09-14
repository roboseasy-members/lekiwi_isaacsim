"""프로젝트 런타임과 검사가 6장의 학생용 기록 코드를 함께 사용합니다."""
from pathlib import Path
import runpy

_source = Path(__file__).resolve().parents[1] / "isaacsim_basic/06_lekiwi_dataset/experiments/01_lekiwi_recording.py"
RecordingPanel = runpy.run_path(str(_source), run_name="lekiwi_recording_lesson")["RecordingPanel"]
