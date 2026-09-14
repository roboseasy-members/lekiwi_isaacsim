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
        # 진행 단계와 오류는 stderr로 보내고 CLI의 stdout은 완료 JSON으로 유지합니다.
        result = subprocess.run(args, stdout=sys.stderr, stderr=sys.stderr, text=True)
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


def build_dataset_card(info, report, repo_id):
    """Describe validated training data without publishing the local source report."""
    successes = sum(source.get('success') is True for source in report.get('sources', []))
    unmarked = sum(source.get('success') is False for source in report.get('sources', []))
    unknown = report['episodes'] - successes - unmarked
    # Match LeRobot's card metadata: only training parquet files form the table.
    # Metadata parquet files have different schemas and must not be mixed in.
    return f'''---
tags:
- LeRobot
- lekiwi
- isaac-sim
task_categories:
- robotics
configs:
- config_name: default
  data_files:
  - split: train
    path: data/*/*.parquet
---

# {repo_id.split('/')[-1]}

Isaac Sim의 LeKiwi 시연을 LeRobot {info['codebase_version']} 형식으로 변환한 데이터셋입니다.

[Visualize Dataset에서 열기](https://huggingface.co/spaces/lerobot/visualize_dataset?path={repo_id})

## 수집 내용

- {report['episodes']}개 에피소드, {report['frames']} 프레임, {info['fps']} FPS
- 전체 길이: {report['frames'] / info['fps']:.2f}초
- 성공 표시: {successes}개 / 성공으로 표시하지 않은 에피소드: {unmarked}개 / 표시 정보 없음: {unknown}개
- 전방·손목 RGB 영상과 9차원 상태·행동을 포함합니다.
- 팔 관절·그리퍼는 rad, 베이스 평면 속도는 m/s, 회전 속도는 rad/s입니다.

성공 표시는 수집자가 저장할 때 지정한 값입니다. 성공으로 표시하지 않은 에피소드를 성공 시연으로 간주하지 않습니다.
데이터셋 라이선스는 아직 지정하지 않았습니다.

## 데이터 구조

`data/`에는 프레임별 수치, `videos/`에는 카메라 영상, `meta/`에는 에피소드·작업·통계 정보가 있습니다.
영상 해상도와 상태·행동의 각 차원 이름은 아래와 같습니다.

```json
{json.dumps(info, ensure_ascii=False, indent=2)}
```
'''


def upload_dataset(name, repo_id, private, token, api_factory=None):
    """Validate a dataset, then upload its training files and generated Hub card."""
    if not isinstance(repo_id, str) or not re.fullmatch(
            r'[A-Za-z0-9][A-Za-z0-9._-]{0,95}/[A-Za-z0-9][A-Za-z0-9._-]{0,95}', repo_id):
        raise UserError('Hugging Face 저장소는 계정명/데이터셋명 형식으로 적으세요.')
    if type(private) is not bool:
        raise UserError('공개 범위는 True 또는 False로 설정하세요.')
    if not isinstance(token, str) or not 16 <= len(token) <= 512 or not re.fullmatch(r'hf_[A-Za-z0-9_-]+', token):
        raise UserError('Hugging Face 쓰기 토큰 형식을 확인하세요.')
    root = dataset_path(name)
    if any(path.is_symlink() for path in root.rglob('*')):
        raise UserError('데이터셋 안의 심볼릭 링크를 사용할 수 없습니다.')
    report = validate_dataset(root)
    dataset_info = read_json(root / 'meta/info.json')
    version = dataset_info.get('codebase_version')
    if version != 'v3.0':
        raise UserError('LeRobot v3.0 데이터셋만 업로드할 수 있습니다.')
    expected_files = {path.relative_to(root).as_posix()
                      for folder in ('data', 'meta', 'videos')
                      for path in (root / folder).rglob('*') if path.is_file()}
    card = build_dataset_card(dataset_info, report, repo_id).encode('utf-8')
    try:
        if api_factory is None:
            from huggingface_hub import HfApi
            api_factory = HfApi
        # HfApi에 직접 전달한 토큰은 hf auth login과 달리 디스크에 저장되지 않습니다.
        api = api_factory(token=token)
        api.whoami()
        api.create_repo(repo_id=repo_id, repo_type='dataset', private=private, exist_ok=True)
        info = api.repo_info(repo_id=repo_id, repo_type='dataset')
        actual_private = getattr(info, 'private', None)
        if actual_private is None and isinstance(info, dict):
            actual_private = info.get('private')
        if actual_private is not private:
            requested = '비공개' if private else '공개'
            raise UserError(f'기존 저장소의 공개 범위가 요청한 {requested} 설정과 다릅니다.')
        parent_commit = info.get('sha') if isinstance(info, dict) else info.sha
        existing = set(api.list_repo_files(repo_id=repo_id, repo_type='dataset', revision=parent_commit))
        refs = api.list_repo_refs(repo_id=repo_id, repo_type='dataset')
        if (existing - {'.gitattributes', 'README.md', '.gitignore'} or
                any(ref.name == version for ref in refs.branches + refs.tags)):
            raise UserError('이미 데이터나 버전 태그가 있는 저장소입니다. 새 저장소 이름을 사용하세요.')
        commit = api.upload_folder(
            folder_path=str(root), repo_id=repo_id, repo_type='dataset',
            allow_patterns=['data/**', 'meta/**', 'videos/**'],
            parent_commit=parent_commit,
            commit_message='Upload validated LeKiwi LeRobot dataset')
        commit_id = str(commit.oid)
        files = set(api.list_repo_files(repo_id=repo_id, repo_type='dataset', revision=commit_id))
        if not expected_files.issubset(files):
            raise UserError('업로드 뒤 학습 파일 일부가 누락됐습니다. 서버의 작업 로그를 확인하세요.')
        commit = api.upload_file(
            path_or_fileobj=card, path_in_repo='README.md',
            repo_id=repo_id, repo_type='dataset', parent_commit=commit_id,
            commit_message='Add LeKiwi dataset card and viewer configuration')
        commit_id = str(commit.oid)
        files = set(api.list_repo_files(repo_id=repo_id, repo_type='dataset', revision=commit_id))
        if not (expected_files | {'README.md'}).issubset(files):
            raise UserError('업로드 뒤 데이터셋 카드 또는 학습 파일이 누락됐습니다.')
        # LeRobot의 기본 Hub 로더는 main 대신 데이터 형식 버전 태그를 찾습니다.
        api.create_tag(repo_id=repo_id, repo_type='dataset', tag=version, revision=commit_id)
        tagged = api.repo_info(repo_id=repo_id, repo_type='dataset', revision=version)
        if tagged.sha != commit_id:
            raise UserError('LeRobot 버전 태그가 이번 업로드를 가리키지 않습니다.')
    except UserError:
        raise
    except Exception as exc:
        status = getattr(getattr(exc, 'response', None), 'status_code', None)
        if status in (401, 403):
            raise UserError('Hugging Face 인증 또는 저장소 쓰기 권한을 확인하세요.') from None
        raise UserError('Hugging Face 업로드에 실패했습니다. 네트워크와 저장소 이름을 확인하세요.') from None
    return {'name': name, 'repo_id': repo_id, 'private': private,
            'frames': report['frames'], 'episodes': report['episodes'],
            'url': f'https://huggingface.co/datasets/{repo_id}',
            'commit': commit_id, 'revision': version}
