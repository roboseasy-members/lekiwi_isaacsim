"""GPU별 설치 분기와 기존 시스템 보존. 실제 패키지·드라이버는 변경하지 않는다."""
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools/host_setup'))
import checks
spec = importlib.util.spec_from_file_location('host_setup_main', ROOT/'tools/host_setup/main.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


def machine(**changes):
    data = dict(os='ubuntu', release='24.04', arch='x86_64', kernel='6.8.0-generic',
                pci=['0000:01:00.0'], ram_gib=15, cpu_threads=16, free_gib=100, display=True,
                gpus=[dict(name='NVIDIA GeForce RTX 5060 Laptop GPU', vram_mib=8151, driver='580.173.02')])
    data.update(changes)
    return data


def test_below_official_memory_is_allowed():
    result = checks.assess(machine())
    assert not result['errors'] and result['driver_ready']
    assert len(result['warnings']) == 2


@pytest.mark.parametrize('name', ['Tesla V100', 'NVIDIA A100-SXM4', 'NVIDIA H100', 'GeForce GTX 1660', 'NVIDIA T4'])
def test_known_non_rt_is_blocked(name):
    result = checks.assess(machine(gpus=[dict(name=name, vram_mib=24000, driver='580.173.02')]))
    assert result['errors']


@pytest.mark.parametrize('changes', [dict(os='debian'), dict(arch='aarch64'), dict(kernel='microsoft-WSL2'), dict(pci=[])])
def test_unsupported_host_is_blocked(changes):
    assert checks.assess(machine(**changes))['errors']


def test_newer_existing_driver_kept_but_not_certified():
    g = dict(name='RTX 5090', vram_mib=32000, driver='595.1.0')
    r = checks.assess(machine(gpus=[g]))
    assert r['driver_ready'] and any('검증 계열' in w for w in r['warnings'])


@pytest.mark.parametrize('gpus', [[], [dict(name='RTX 3060', vram_mib=12000, driver='535.100.0')]])
def test_missing_or_old_driver_needs_preparation(gpus):
    assert not checks.assess(machine(gpus=gpus))['driver_ready']


DEVICE = '''== /sys/devices/gpu0 ==
modalias : pci:v000010DEd00002D19
vendor : NVIDIA Corporation
driver : nvidia-driver-595-open - distro non-free recommended
driver : nvidia-driver-580-open - distro non-free
driver : nvidia-driver-580 - distro non-free
'''


def test_supported_validated_branch_wins_over_newest_recommended():
    assert checks.select_driver(DEVICE, {'nvidia-driver-580-open': '580.173.02-0ubuntu1'}) == 'nvidia-driver-580-open'


@pytest.mark.parametrize('candidate', ['(none)', '580.60.01-0ubuntu1', '595.12.0-0ubuntu1'])
def test_missing_old_or_transitional_candidate_is_not_selected(candidate):
    assert checks.select_driver(DEVICE, {'nvidia-driver-580-open': candidate}) is None


def test_multiple_gpus_use_intersection_and_can_fall_back_to_proprietary():
    other = '== /sys/devices/gpu1 ==\nvendor : NVIDIA\ndriver : nvidia-driver-580 - distro non-free\n'
    versions = {'nvidia-driver-580-open': '580.173.02', 'nvidia-driver-580': '580.173.02'}
    assert checks.select_driver(DEVICE+other, versions) == 'nvidia-driver-580'
    assert checks.select_driver(DEVICE+other.replace('580', '470'), versions) is None


def test_reboot_gate_does_not_repeat_driver_install():
    with pytest.raises(RuntimeError, match='재부팅이 필요'):
        setup.reboot_gate({'driver_boot': 'old'}, 'old', True)
    with pytest.raises(RuntimeError, match='자동 재설치'):
        setup.reboot_gate({'driver_boot': 'old'}, 'new', False)
    setup.reboot_gate({'driver_boot': 'old'}, 'new', True)


def test_check_only_never_requests_sudo_or_writes_state(monkeypatch):
    monkeypatch.setattr(setup, 'inspect', lambda root: machine())
    monkeypatch.setattr(sys, 'argv', ['setup', '--check'])
    def forbidden(*args, **kwargs):
        pytest.fail('읽기 전용 모드가 시스템 변경을 시도함')
    for name in ('run', 'confirm', 'save_state', 'install_driver', 'install_host', 'verify'):
        monkeypatch.setattr(setup, name, forbidden)
    setup.main()


def test_compatible_driver_runs_no_package_commands(monkeypatch):
    monkeypatch.setattr(setup, 'run', lambda *a, **kw: pytest.fail('기존 드라이버를 변경함'))
    setup.install_driver(machine())


def test_no_confirmation_from_noninteractive_input(monkeypatch):
    monkeypatch.setattr(sys.stdin, 'isatty', lambda: False)
    with pytest.raises(RuntimeError, match='승인하지'):
        setup.confirm('설치')


def test_remote_docker_refused_before_privileged_commands(monkeypatch):
    monkeypatch.setenv('DOCKER_HOST', 'ssh://remote')
    monkeypatch.setattr(setup, 'run', lambda *a, **kw: pytest.fail('원격 환경에서 변경함'))
    with pytest.raises(RuntimeError, match='DOCKER_HOST'):
        setup.docker_command()


def test_ready_host_does_not_install_or_restart(monkeypatch):
    def query(args):
        if args[0] == 'dpkg-query': return 'installed'
        if args[:3] == ['docker', 'compose', 'version']: return '2.30.1'
        if args[:3] == ['docker', 'buildx', 'version']: return 'v0.30.0'
        if '.Runtimes' in args[-1]: return '{"nvidia": {}, "runc": {}}'
        pytest.fail(str(args))
    monkeypatch.setattr(setup, 'query', query)
    monkeypatch.setattr(setup, 'docker_command', lambda: ['docker'])
    monkeypatch.setattr(setup, 'docker_query', lambda docker, args: query(docker+args))
    monkeypatch.setattr(setup, 'confirm', lambda *a: pytest.fail('완료된 설치를 재확인함'))
    monkeypatch.setattr(setup, 'run', lambda *a, **kw: pytest.fail('준비된 환경을 수정함'))
    assert setup.install_host(dict(docker=True, toolkit=True)) == ['docker']


def test_running_containers_prevent_runtime_edit_and_restart(monkeypatch):
    def query(args):
        if args[0] == 'dpkg-query': return 'installed'
        if args[:3] == ['docker', 'compose', 'version']: return '2.30.1'
        if args[:3] == ['docker', 'buildx', 'version']: return 'v0.30.0'
        if args[-2:] == ['ps', '-q']: return 'other-student-job'
        return '{"runc": {}}'
    monkeypatch.setattr(setup, 'query', query)
    monkeypatch.setattr(setup, 'docker_command', lambda: ['docker'])
    monkeypatch.setattr(setup, 'docker_query', lambda docker, args: query(docker+args))
    monkeypatch.setattr(setup, 'run', lambda *a, **kw: pytest.fail('실행 중 daemon을 수정함'))
    with pytest.raises(RuntimeError, match='실행 중인 컨테이너'):
        setup.install_host(dict(docker=True, toolkit=True))


def test_driver_csv_preserves_multiple_devices():
    result = checks.parse_gpus('RTX 3060, 12288, 580.65.06\nRTX 5090, 32768, 580.173.02')
    assert len(result) == 2 and result[0]['vram_mib'] == 12288
    assert checks.parse_gpus('Failed to initialize NVML') == []


def test_default_context_with_remote_endpoint_is_rejected(monkeypatch):
    monkeypatch.delenv('DOCKER_HOST', raising=False)
    monkeypatch.delenv('DOCKER_CONTEXT', raising=False)
    monkeypatch.setattr(setup, 'query', lambda args: 'default' if args[-1] == 'show' else 'ssh://remote')
    monkeypatch.setattr(setup, 'run', lambda *a, **kw: pytest.fail('원격 daemon에 변경 시도'))
    with pytest.raises(RuntimeError, match='시스템 로컬 소켓'):
        setup.docker_command()


def test_failed_docker_status_is_not_an_empty_container_list(monkeypatch):
    import subprocess
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])
    monkeypatch.setattr(subprocess, 'run', fail)
    with pytest.raises(subprocess.CalledProcessError):
        setup.docker_query(['docker'], ['ps', '-q'])


def test_verify_does_not_install_even_with_os_reboot_flag(monkeypatch):
    info = machine(docker=True)
    monkeypatch.setattr(setup, 'inspect', lambda root: info)
    monkeypatch.setattr(setup.os, 'geteuid', lambda: 1000)
    monkeypatch.setattr(setup, 'read', lambda path: '' if str(path).endswith('.json') else 'boot')
    monkeypatch.setattr(setup, 'query', lambda args: 'default' if args[-1] == 'show' else 'unix:///var/run/docker.sock')
    monkeypatch.setattr(setup.Path, 'exists', lambda self: True)
    monkeypatch.setattr(setup, 'docker_command', lambda: ['docker'])
    called = []
    monkeypatch.setattr(setup, 'verify', lambda docker: called.append(docker))
    monkeypatch.setattr(setup, 'install_driver', lambda info: pytest.fail('검사 중 드라이버 설치'))
    monkeypatch.setattr(setup, 'install_host', lambda info: pytest.fail('검사 중 패키지 설치'))
    monkeypatch.delenv('DOCKER_HOST', raising=False)
    monkeypatch.delenv('DOCKER_CONTEXT', raising=False)
    monkeypatch.setattr(sys, 'argv', ['setup', '--verify'])
    setup.main()
    assert called == [['docker']]


def test_verify_missing_image_never_builds_or_runs(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setenv('ACCEPT_EULA', 'Y')
    monkeypatch.setattr(setup.subprocess, 'run', lambda *a, **kw: SimpleNamespace(stdout='lekiwi-sim:0.1.0\n'))
    monkeypatch.setattr(setup, 'query', lambda args: '')
    monkeypatch.setattr(setup, 'run', lambda *a, **kw: pytest.fail('없는 이미지를 자동 빌드'))
    with pytest.raises(RuntimeError, match='이미지가 없습니다'):
        setup.verify(['docker'])


def test_fresh_host_prepares_official_packages_without_deleting_existing_data(monkeypatch):
    commands, sources, questions = [], [], []
    def query(args):
        if args[0] == 'dpkg-query': return ''
        if args[:3] == ['docker', 'compose', 'version']: return '2.30.1'
        if args[:3] == ['docker', 'buildx', 'version']: return 'v0.30.0'
        return ''
    monkeypatch.setattr(setup, 'query', query)
    monkeypatch.setattr(setup, 'confirm', questions.append)
    monkeypatch.setattr(setup, 'run', lambda args, **kwargs: commands.append(list(map(str, args))))
    monkeypatch.setattr(setup, 'install_source', lambda *args: sources.append(args))
    monkeypatch.setattr(setup, 'docker_command', lambda: ['sudo', 'docker'])
    monkeypatch.setattr(setup, 'docker_query', lambda docker, args: '{"runc": {}}' if args[0] == 'info' else '')
    from types import SimpleNamespace
    monkeypatch.setattr(setup.subprocess, 'run', lambda *a, **kw: SimpleNamespace(returncode=1))
    assert setup.install_host(dict(docker=False, toolkit=False, codename='jammy')) == ['sudo', 'docker']
    assert {s[0] for s in sources} == {'lekiwi-docker', 'lekiwi-nvidia-container'}
    assert any('docker-ce' in c and 'docker-compose-plugin' in c for c in commands)
    assert any('nvidia-container-toolkit' in c for c in commands)
    assert commands[-2:] == [['nvidia-ctk', 'runtime', 'configure', '--runtime=docker'], ['systemctl', 'restart', 'docker']]
    assert not any('purge' in c or 'remove' in c or 'autoremove' in c for c in commands)
    assert not any('cuda-toolkit' in arg for c in commands for arg in c)
    assert len(questions) == 2


def test_driver_install_uses_selected_branch_and_stops_for_reboot(monkeypatch):
    commands, states = [], []
    info = machine(gpus=[], secure_boot='SecureBoot enabled')
    monkeypatch.setattr(setup.Path, 'exists', lambda self: False)
    monkeypatch.setattr(setup, 'confirm', lambda text: None)
    monkeypatch.setattr(setup, 'run', lambda args, **kw: commands.append(args))
    monkeypatch.setattr(setup, 'candidate', lambda name: '580.173.02-0ubuntu1')
    monkeypatch.setattr(setup, 'query', lambda args: DEVICE if args[0] == 'ubuntu-drivers' else 'Depends: nvidia-dkms-580-open')
    monkeypatch.setattr(setup, 'read', lambda path: 'current-boot')
    monkeypatch.setattr(setup, 'save_state', states.append)
    with pytest.raises(RuntimeError, match='직접 재부팅'):
        setup.install_driver(info)
    assert commands[-1] == ['ubuntu-drivers', 'install', 'nvidia:580-open']
    assert states == [{'driver_boot': 'current-boot', 'driver_package': 'nvidia-driver-580-open'}]
    assert not any('reboot' in c for c in commands)
