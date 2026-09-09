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
    (root / 'meta/info.json').write_text('{}')
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
