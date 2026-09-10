"""학생 파일을 새로 읽는 실행 경로와 안전한 import 계약을 검사합니다."""
import importlib.util
from pathlib import Path
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[1]
namespace = runpy.run_path(str(ROOT / 'isaacsim_basic/run.py'))


@pytest.mark.parametrize('chapter', range(1, 7))
def test_chapters_select_an_existing_student_file(chapter):
    path = namespace['script_path'](namespace['CHAPTERS'][chapter])
    assert path.parent.name == 'experiments'
    compile(path.read_text(), str(path), 'exec')


@pytest.mark.parametrize('name', ['../lekiwi', '../outside/experiments/test.py', 'run.py', '/etc/passwd'])
def test_script_selection_rejects_outside_and_non_student_files(name):
    with pytest.raises(ValueError):
        namespace['script_path'](name)


def test_loading_scene_function_does_not_start_isaac_and_reads_saved_changes(tmp_path):
    module = runpy.run_path(str(ROOT / 'isaacsim_basic/experiments.py'))
    path = tmp_path / module['SCRIPTS'][1]
    guard = '\nif __name__ == "__main__":\n    raise RuntimeError("must not launch")\n'
    path.write_text('def build_scene(stage): return "before"\n' + guard)
    assert module['load_experiment'](1, tmp_path)(None) == 'before'
    path.write_text('def build_scene(stage): return "after"\n' + guard)
    assert module['load_experiment'](1, tmp_path)(None) == 'after'


@pytest.mark.parametrize('path', sorted((ROOT / 'isaacsim_basic').glob('0[1-5]*/experiments/*.py')))
def test_foundational_scripts_import_without_isaac_or_project_helpers(path):
    # 앱을 띄우거나 pxr/omni를 import하는 최상위 부작용도 이 환경에서 발견됩니다.
    values = runpy.run_path(str(path), run_name='student_test')
    assert callable(values['build_scene']) and callable(values['main'])
