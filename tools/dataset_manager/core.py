"""Shared dataset operations for CLI and the local classroom UI."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

DATA = Path('/data')


class UserError(ValueError):
    pass


def read_json(path):
    return json.loads(Path(path).read_text())


def safe_error(exc):
    if isinstance(exc, UserError):
        return str(exc)
    return f'작업 실패 ({type(exc).__name__}). 입력 파일·디스크 공간을 확인하세요. 기존 원본은 보존됩니다.'


def dataset_path(name, new=False):
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}', name):
        raise UserError('로컬 이름은 영문·숫자로 시작하고 영문·숫자·점·밑줄·하이픈만 사용하세요.')
    root = DATA / 'datasets'
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    if path.is_symlink() or path.resolve().parent != root.resolve():
        raise UserError('심볼릭 링크 경로는 사용할 수 없습니다.')
    if new and path.exists():
        raise UserError('같은 이름의 로컬 폴더가 있습니다. 새 이름을 입력하세요.')
    return path


@contextmanager
def operation_lock():
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / '.dataset-manager.lock').open('a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise UserError('다른 데이터셋 작업이 실행 중입니다. 완료 후 다시 시도하세요.') from None
        yield


def inventory():
    episodes, datasets = [], []
    for path in sorted((DATA / 'recordings').glob('lekiwi.*/episode.*')):
        if path.name.endswith('.partial') or path.is_symlink():
            continue
        try:
            m = read_json(path / 'manifest.json')
            if m.get('complete') is not True:
                continue
            episodes.append({'id': str(path.relative_to(DATA / 'recordings')), 'task': m['task'],
                             'frames': m['frames'], 'success': m['success'], 'source': m['source']})
        except (OSError, ValueError, KeyError):
            continue
    for path in sorted((DATA / 'datasets').glob('*')):
        if path.name.startswith('.') or path.is_symlink():
            continue
        try:
            m = read_json(path / 'recording_report.json')
            if m.get('complete') is True:
                datasets.append({'name': path.name, 'frames': m['frames'], 'episodes': m['episodes'],
                                 'repo_id': m['repo_id']})
        except (OSError, ValueError, KeyError):
            continue
    return {'episodes': episodes, 'datasets': datasets}


def episode_path(value):
    if not isinstance(value, str) or not re.fullmatch(r'lekiwi\.[\w-]+/episode\.[\w-]+', value):
        raise UserError('완료된 에피소드를 선택하세요.')
    root = DATA / 'recordings'
    path = root / value
    if path.is_symlink() or path.parent.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise UserError('에피소드 경로를 확인하세요.')
    if not (path / 'manifest.json').is_file():
        raise UserError('완료된 에피소드가 아닙니다.')
    return path


def export_selected(episodes, name, success_only=False):
    dest = dataset_path(name, new=True)
    repo_id = f'local/{name}'
    if not isinstance(episodes, list) or not episodes or len(set(episodes)) != len(episodes):
        raise UserError('중복 없이 하나 이상의 에피소드를 선택하세요.')
    paths = [episode_path(e) for e in episodes]
    # The existing exporter validates every raw frame. A private temporary input
    # directory combines sessions without copying or changing original recordings.
    with tempfile.TemporaryDirectory(prefix='.export-', dir=dest.parent) as tmp:
        for n, path in enumerate(paths):
            (Path(tmp) / f'episode.{n:06}').symlink_to(path, target_is_directory=True)
        script = Path(__file__).resolve().parents[1] / 'export_dataset.py'
        args = [sys.executable, str(script), '--input', tmp, '--output', str(dest), '--repo-id', repo_id]
        if success_only:
            args.append('--success-only')
        result = subprocess.run(args, capture_output=True, text=True)
        if result.returncode:
            raise UserError('변환 실패: 원본 검사·카메라 설정 일치 여부·디스크 공간을 확인하세요. 미완성 출력은 보존되며 재시도에는 새 이름이 필요합니다.')
    report = read_json(dest / 'recording_report.json')
    # Replace temporary symlink names with durable source identities.
    for source in report['sources']:
        index = int(Path(source['path']).name.split('.')[1])
        source['path'] = str(paths[index])
    (dest / 'recording_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return {'name': name, 'frames': report['frames'], 'episodes': report['episodes']}


def validate_dataset(root):
    # Set offline mode before importing the dataset libraries.
    result = subprocess.run(
        [sys.executable, str(Path(__file__).with_name('cli.py')), '_validate', str(root)],
        env=dict(os.environ, HF_HUB_OFFLINE='1'), capture_output=True, text=True)
    if result.returncode:
        raise UserError('데이터셋 검사가 실패했습니다. 완료 기록·로봇 규격·영상 파일을 확인하세요.')
    return read_json(root / 'recording_report.json')


def _validate_dataset(root):
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    import numpy as np
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'isaac_sim'))
    from episode_data import ACTION_NAMES, STATE_NAMES
    report = read_json(root / 'recording_report.json')
    info = read_json(root / 'meta/info.json')
    if report.get('complete') is not True or info.get('robot_type') != 'lekiwi_sim' or info.get('fps') != 30:
        raise UserError('이 도구에서 지원하는 완료된 LeKiwi 30 Hz 데이터셋이 아닙니다.')
    for key, names in (('action', ACTION_NAMES), ('observation.state', STATE_NAMES)):
        f = info['features'][key]
        if f['shape'] != [9] or f['names'] != names:
            raise UserError('학습 데이터의 관절·베이스 순서가 현재 로봇과 다릅니다.')
    for camera in ('front', 'wrist'):
        w, h = report['camera_config']['cameras'][camera]['resolution']
        f = info['features'][f'observation.images.{camera}']
        if f['dtype'] != 'video' or f['shape'] != [h, w, 3]:
            raise UserError('카메라 영상 규격이 기록 설정과 다릅니다.')
    ds = LeRobotDataset(repo_id=report['repo_id'], root=root, video_backend='pyav')
    if len(ds) != report['frames'] or ds.num_episodes != report['episodes'] or len(ds) < 1:
        raise UserError('데이터셋 프레임·에피소드 수가 검사 결과와 다릅니다.')
    for i in sorted({0, len(ds) // 2, len(ds) - 1}):
        item = ds[i]
        for key in ('action', 'observation.state', 'observation.images.front', 'observation.images.wrist'):
            if not np.isfinite(item[key].numpy()).all():
                raise UserError('데이터셋에 유효하지 않은 수치가 있습니다.')
    return report


def inspect_dataset(name):
    root = dataset_path(name)
    if any(path.is_symlink() for path in root.rglob('*')):
        raise UserError('데이터셋 안의 심볼릭 링크를 사용할 수 없습니다.')
    report = validate_dataset(root)
    return {'name': name, 'path': str(root), 'repo_id': report['repo_id'],
            'frames': report['frames'], 'episodes': report['episodes']}
