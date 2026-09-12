"""Local dataset management tests; no network service or robot needed."""
import importlib.util
import json
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dataset_core_test', ROOT / 'tools/dataset_manager/core.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


@pytest.fixture
def area(tmp_path, monkeypatch):
    monkeypatch.setattr(core, 'DATA', tmp_path)
    return tmp_path


def local_dataset(area):
    root = area / 'datasets' / 'sample'
    (root / 'meta').mkdir(parents=True)
    (root / 'data/chunk-000').mkdir(parents=True)
    (root / 'meta/info.json').write_text(json.dumps({
        'codebase_version': 'v3.0', 'fps': 30, 'robot_type': 'lekiwi_sim', 'features': {}}))
    (root / 'data/chunk-000/file-000.parquet').write_bytes(b'dataset bytes')
    report = {'complete': True, 'repo_id': 'student/example', 'episodes': 1, 'frames': 3}
    (root / 'recording_report.json').write_text(json.dumps(report))
    return root, report


@pytest.mark.parametrize('name', ['../cache', '/data/cache', '.hidden', '', 'a/b', 'bad name'])
def test_dataset_names_cannot_escape_or_target_cache(area, name):
    with pytest.raises(core.UserError):
        core.dataset_path(name)


def test_existing_output_and_symlinks_are_never_overwritten(area):
    root, _ = local_dataset(area)
    with pytest.raises(core.UserError):
        core.dataset_path('sample', new=True)
    (root.parent / 'link').symlink_to(root)
    with pytest.raises(core.UserError):
        core.dataset_path('link')


def test_concurrent_operations_refused(area):
    with core.operation_lock():
        with pytest.raises(core.UserError, match='다른 데이터셋'):
            with core.operation_lock(): pass


def test_unknown_errors_do_not_echo_token_or_headers():
    secret = 'a-sensitive-placeholder'
    assert secret not in core.safe_error(RuntimeError(secret))


def test_validation_subprocess_is_offline(area, monkeypatch):
    root, report = local_dataset(area)
    def run(args, **kwargs):
        assert kwargs['env']['HF_HUB_OFFLINE'] == '1'
        assert args[-2:] == ['_validate', str(root)]
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(core.subprocess, 'run', run)
    assert core.validate_dataset(root) == report


def test_export_rejects_incomplete_or_traversal_before_running(area, monkeypatch):
    monkeypatch.setattr(core.subprocess, 'run', lambda *a, **k: pytest.fail('must not run'))
    for episodes in ([], ['../cache'], ['lekiwi.a/episode.b.partial'], ['lekiwi.a/episode.b']):
        with pytest.raises(core.UserError):
            core.export_selected(episodes, 'new')


@pytest.fixture
def http_app(area, monkeypatch):
    monkeypatch.setitem(sys.modules, 'core', core)
    spec = importlib.util.spec_from_file_location('dataset_server_test', ROOT/'tools/dataset_manager/server.py')
    server_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server_module)
    app = server_module.App()
    server = ThreadingHTTPServer(('127.0.0.1', 0), server_module.make_handler(app))
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    yield app, server.server_port
    server.shutdown(); server.server_close(); thread.join()


def request(port, path='/api/list', data=None, **headers):
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}',
                                 data=json.dumps(data).encode() if data is not None else None,
                                 headers={'Host':'127.0.0.1:8765', **headers})
    return urllib.request.urlopen(req, timeout=3)


def test_ui_rejects_missing_key_and_foreign_origin(http_app):
    app, port = http_app
    with pytest.raises(urllib.error.HTTPError) as e: request(port)
    assert e.value.code == 403
    with request(port, **{'X-LeKiwi-Key':app.key}) as r:
        assert json.load(r) == {'episodes':[], 'datasets':[]}
    for origin in ('https://evil.example', 'null'):
        with pytest.raises(urllib.error.HTTPError) as e:
            request(port, '/api/job', {'operation':'logout'}, **{
                'X-LeKiwi-Key':app.key, 'Content-Type':'application/json','Origin':origin})
        assert e.value.code == 403
    with pytest.raises(urllib.error.HTTPError):
        request(port, '/', Host='evil.example')


def test_ui_background_inspection_keeps_server_responsive(http_app, monkeypatch):
    app, port = http_app
    started, release = threading.Event(), threading.Event()
    def inspect(name):
        started.set(); release.wait(3)
        return {'name':name,'frames':3,'episodes':1}
    monkeypatch.setattr(core, 'inspect_dataset', inspect)
    args={'name':'sample'}
    app.submit('inspect',args)
    assert started.wait(2)
    try:
        with pytest.raises(core.UserError): app.submit('inspect',{})
        with request(port, '/api/state', **{'X-LeKiwi-Key':app.key}) as r:
            state=json.load(r)
            assert state['busy'] is True
    finally: release.set()


def test_new_export_reports_durable_original_sources(area, monkeypatch):
    paths = ['lekiwi.one/episode.first', 'lekiwi.two/episode.second']
    for value in paths:
        p=area/'recordings'/value
        p.mkdir(parents=True)
        (p/'manifest.json').write_text('{}')
    def run(args, **kwargs):
        source=Path(args[args.index('--input')+1]); dest=Path(args[args.index('--output')+1])
        assert [p.resolve() for p in sorted(source.glob('episode.*'))] == [area/'recordings'/p for p in paths]
        dest.mkdir()
        (dest/'recording_report.json').write_text(json.dumps({'frames':2,'episodes':2,
            'sources':[{'path':str(p)} for p in sorted(source.glob('episode.*'))]}))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(core.subprocess,'run',run)
    core.export_selected(paths,'combined')
    report=core.read_json(area/'datasets/combined/recording_report.json')
    assert [s['path'] for s in report['sources']] == [str(area/'recordings'/p) for p in paths]
    assert not list((area/'datasets').glob('.export-*'))


@pytest.mark.parametrize('operation', ['login', 'whoami', 'logout', 'upload', 'download', 'plan-upload'])
def test_removed_hub_operations_rejected_by_server(http_app, operation):
    app, _ = http_app
    with pytest.raises(core.UserError, match='지원하지'):
        app.submit(operation, {})
    assert app.state['busy'] is False


def test_inspection_preserves_original_report_and_uses_local_path(area, monkeypatch):
    root, report = local_dataset(area)
    monkeypatch.setattr(core, 'validate_dataset', lambda p: report if p == root else pytest.fail('wrong root'))
    result = core.inspect_dataset('sample')
    assert result['frames'] == 3 and result['path'] == str(root)
    assert core.read_json(root/'recording_report.json') == report
    (root/'leak').symlink_to(area)
    with pytest.raises(core.UserError): core.inspect_dataset('sample')


@pytest.mark.parametrize('remote_state', ['empty', 'existing_data', 'existing_tag', 'missing_file',
                                        'missing_card', 'card_failure', 'wrong_tag'])
def test_upload_validates_then_sends_only_lerobot_files(area, monkeypatch, remote_state):
    root, report = local_dataset(area)
    (root / 'meta/stats.json').write_text('{}')
    (root / 'videos/observation.images.front/chunk-000').mkdir(parents=True)
    (root / 'videos/observation.images.wrist/chunk-000').mkdir(parents=True)
    (root / 'videos/observation.images.front/chunk-000/file-000.mp4').write_bytes(b'front')
    (root / 'videos/observation.images.wrist/chunk-000/file-000.mp4').write_bytes(b'wrist')
    calls = []
    monkeypatch.setattr(core, 'validate_dataset', lambda path: calls.append(('validate', path)) or report)

    class Api:
        def __init__(self, token):
            assert token == 'hf_test_token_123456789'
            calls.append(('api',))
            self.uploaded = False
            self.card_uploaded = False
        def whoami(self): calls.append(('whoami',))
        def create_repo(self, **kwargs): calls.append(('create', kwargs))
        def repo_info(self, **kwargs):
            calls.append(('info', kwargs))
            sha = ('oldcommit' if remote_state == 'wrong_tag' else 'card123') if kwargs.get('revision') else 'initial123'
            return SimpleNamespace(private=True, sha=sha)
        def list_repo_refs(self, **kwargs):
            return SimpleNamespace(branches=[SimpleNamespace(name='main')],
                tags=[SimpleNamespace(name='v3.0')] if remote_state == 'existing_tag' else [])
        def upload_folder(self, **kwargs):
            calls.append(('upload', kwargs))
            self.uploaded = True
            return SimpleNamespace(oid='commit123')
        def upload_file(self, **kwargs):
            calls.append(('card', kwargs))
            if remote_state == 'card_failure':
                raise RuntimeError('upload failed')
            self.card_uploaded = True
            return SimpleNamespace(oid='card123')
        def list_repo_files(self, **kwargs):
            if not self.uploaded:
                return ['.gitattributes', 'README.md'] + (['data/chunk-000/file-000.parquet']
                    if remote_state == 'existing_data' else [])
            files = ['meta/info.json', 'data/chunk-000/file-000.parquet',
                    'videos/observation.images.front/chunk-000/file-000.mp4',
                    'videos/observation.images.wrist/chunk-000/file-000.mp4']
            files += [] if remote_state == 'missing_file' else ['meta/stats.json']
            if self.card_uploaded and remote_state != 'missing_card':
                files.append('README.md')
            return files
        def create_tag(self, **kwargs): calls.append(('tag', kwargs))

    if remote_state != 'empty':
        with pytest.raises(core.UserError):
            core.upload_dataset('sample', 'student/lekiwi-data', True,
                                'hf_test_token_123456789', Api)
        if remote_state.startswith('existing_'):
            assert not any(entry[0] in ('upload', 'card', 'tag') for entry in calls)
        if remote_state in ('missing_file', 'missing_card', 'card_failure'):
            assert not any(entry[0] == 'tag' for entry in calls)
        return

    result = core.upload_dataset('sample', 'student/lekiwi-data', True,
                                 'hf_test_token_123456789', Api)
    assert calls[0] == ('validate', root)
    upload = next(entry[1] for entry in calls if entry[0] == 'upload')
    assert upload['allow_patterns'] == ['data/**', 'meta/**', 'videos/**']
    assert upload['parent_commit'] == 'initial123'
    assert 'recording_report.json' not in upload['allow_patterns']
    assert result['url'] == 'https://huggingface.co/datasets/student/lekiwi-data'
    card = next(entry[1] for entry in calls if entry[0] == 'card')
    assert card['path_in_repo'] == 'README.md'
    assert card['parent_commit'] == 'commit123'
    assert card['repo_id'] == 'student/lekiwi-data'
    assert isinstance(card['path_or_fileobj'], bytes)
    assert b'configs:' in card['path_or_fileobj']
    assert not (root / 'README.md').exists()
    assert result['commit'] == 'card123'
    assert result['revision'] == 'v3.0'
    assert next(entry[1] for entry in calls if entry[0] == 'tag') == {
        'repo_id': 'student/lekiwi-data', 'repo_type': 'dataset',
        'tag': 'v3.0', 'revision': 'card123'}
    assert calls[-1] == ('info', {'repo_id': 'student/lekiwi-data', 'repo_type': 'dataset', 'revision': 'v3.0'})


def test_upload_refuses_visibility_mismatch_and_masks_remote_secret(area, monkeypatch):
    root, report = local_dataset(area)
    monkeypatch.setattr(core, 'validate_dataset', lambda path: report)
    uploaded = []
    class PublicApi:
        def __init__(self, token): pass
        def whoami(self): pass
        def create_repo(self, **kwargs): pass
        def repo_info(self, **kwargs): return SimpleNamespace(private=False)
        def upload_folder(self, **kwargs): uploaded.append(kwargs)
    with pytest.raises(core.UserError, match='공개 범위'):
        core.upload_dataset('sample', 'student/existing', True, 'hf_test_token_123456789', PublicApi)
    assert uploaded == []

    secret = 'hf_secret_that_must_not_appear'
    class FailingApi:
        def __init__(self, token): pass
        def whoami(self): raise RuntimeError(secret)
    with pytest.raises(core.UserError) as failure:
        core.upload_dataset('sample', 'student/new', True, secret, FailingApi)
    assert secret not in str(failure.value)


def test_dataset_card_describes_data_without_disclosing_local_report(area):
    root, report = local_dataset(area)
    report['sources'] = [{'path': '/private/recordings/episode', 'success': False}]
    card = core.build_dataset_card(core.read_json(root / 'meta/info.json'), report, 'student/test')
    assert 'data/*/*.parquet' in card
    assert 'task_categories:\n- robotics' in card
    assert 'visualize_dataset?path=student/test' in card
    assert '3 프레임' in card
    assert '성공 표시: 0개' in card
    assert '/private/' not in card
    assert 'student/example' not in card
    assert 'license:' not in card  # Dataset owners choose their own license.
