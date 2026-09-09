"""Ubuntu 학생용 준비 도구. 시스템 Python 표준 라이브러리만 사용한다."""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time
import urllib.request

from checks import assess, inspect, query, read, select_driver, version

ROOT = Path(__file__).resolve().parents[2]


def run(args, *, admin=False, env=None):
    command = (['sudo'] if admin else []) + [str(a) for a in args]
    print('+ ' + shlex.join(command), flush=True)
    subprocess.run(command, check=True, env=env)


def confirm(message):
    print(message, flush=True)
    if not sys.stdin.isatty() or input('진행하려면 y 입력 [y/N]: ').strip().lower() != 'y':
        raise RuntimeError('변경을 승인하지 않아 중단했습니다. 다시 실행할 수 있습니다.')


def state_path():
    return Path(os.environ.get('LEKIWI_DATA_DIR', str(ROOT/'data')))/'setup/host-state.json'


def save_state(data):
    p = state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    temporary = p.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    temporary.replace(p)


def reboot_gate(state, boot, ready):
    if state.get('driver_boot') == boot:
        raise RuntimeError('드라이버 설치 후 재부팅이 필요합니다. 재부팅하고 ./lekiwi install을 다시 실행하세요.')
    if state.get('driver_boot') and not ready:
        raise RuntimeError('재부팅 후에도 580 계열(580.65.06 이상) 드라이버가 준비되지 않았습니다. nvidia-smi의 실제 버전과 Secure Boot의 MOK 등록을 확인하세요. 자동 재설치는 하지 않습니다.')


def candidate(package):
    import re
    m = re.search(r'Candidate:\s+(\S+)', query(['apt-cache', 'policy', package]))
    return m[1] if m else ''


def docker_query(docker, args):
    """daemon 상태 조회 실패를 '실행 중인 작업 없음'으로 해석하지 않는다."""
    return subprocess.run(docker+args, capture_output=True, text=True, check=True, timeout=30).stdout.strip()


def install_driver(info):
    if assess(info)['driver_ready']:
        print('580 계열(580.65.06 이상)의 로드된 드라이버 유지. 실제 렌더링 검사는 별도 수행합니다.')
        return
    if Path('/sys/module/nvidia').exists() and (not info['gpus'] or len(info['gpus']) != len(info['pci'])):
        raise RuntimeError('NVIDIA 모듈이 로드됐지만 모든 GPU를 읽지 못했습니다. nvidia-smi 오류를 먼저 해결하세요. 자동 재설치는 하지 않습니다.')
    if Path('/usr/bin/nvidia-uninstall').exists():
        raise RuntimeError('.run 방식 드라이버가 감지되었습니다. APT 설치와 혼합하지 말고 먼저 설치 방식을 정리하세요.')
    confirm('드라이버 후보 확인용 ubuntu-drivers-common과 pciutils를 Ubuntu 저장소에서 준비합니다.')
    run(['apt-get', 'update'], admin=True)
    run(['apt-get', 'install', '--no-remove', 'ubuntu-drivers-common', 'pciutils'], admin=True)
    devices = query(['ubuntu-drivers', 'devices'])
    packages = ['nvidia-driver-580-open', 'nvidia-driver-580']
    selected = select_driver(devices, {p: candidate(p) for p in packages})
    if not selected:
        raise RuntimeError('모든 NVIDIA GPU를 지원하는 580 계열 후보가 없습니다. 강사와 드라이버/Isaac Sim 버전 조합을 검토하세요.')
    # Ubuntu의 전환 패키지가 다른 계열을 설치하는 경우에는 자동 진행하지 않는다.
    import re
    target = selected+'='+candidate(selected)
    description = query(['apt-cache', 'show', target])
    if not description:
        raise RuntimeError('드라이버 후보의 패키지 정보를 읽지 못했습니다. 자동 설치를 중단합니다.')
    other = set(re.findall(r'nvidia-(?:driver|dkms|kernel-source)-(\d+)', description)) - {'580'}
    if other:
        raise RuntimeError('드라이버 후보가 다른 계열로 전환되는 패키지입니다. 자동 설치를 중단합니다.')
    # 현재 커널의 DKMS 빌드 준비와 의존성 해결이 가능한지 변경 전에 확인한다.
    packages = [target, 'linux-headers-'+info['kernel']]
    run(['apt-get', '--simulate', 'install', *packages])
    current = ', '.join(sorted({g['driver'] for g in info['gpus']})) or '확인되지 않음'
    confirm(f'현재 드라이버: {current} → {selected} 설치. 595 등 다른 계열도 580으로 교체하며 재부팅이 필요합니다.\n'
            '작업을 저장하고 Isaac Sim·학습 등 GPU 작업을 종료한 뒤 진행하세요.\n'
            f"Secure Boot: {info['secure_boot']}. 등록 화면이 나오면 학생이 직접 완료해야 합니다.")
    # 실패 후 반복 설치를 막기 위해 시도 전 부팅 ID를 기록한다.
    save_state({'driver_boot': read('/proc/sys/kernel/random/boot_id'), 'driver_package': selected})
    run(['apt-get', 'install', *packages], admin=True)
    raise RuntimeError('드라이버 설치 완료. 작업을 저장하고 직접 재부팅한 뒤 ./lekiwi install을 다시 실행하세요.')


def install_source(name, key_url, source):
    """공식 HTTPS 키만 받아 전용 파일에 설치한다. 다른 저장소 파일은 보존한다."""
    key = Path('/etc/apt/keyrings')/(name+'.asc')
    dest = Path('/etc/apt/sources.list.d')/(name+'.list')
    if dest.exists():
        if read(dest) != source.strip() or not key.exists():
            raise RuntimeError(f'{dest}의 기존 설정이 예상과 다릅니다. 덮어쓰지 않습니다.')
        return
    domain = 'download.docker.com' if name == 'lekiwi-docker' else 'nvidia.github.io/libnvidia-container'
    for existing in Path('/etc/apt/sources.list.d').glob('*'):
        if existing.suffix in {'.list', '.sources'} and domain in read(existing):
            print(f'기존 공식 저장소 설정 사용: {existing}')
            return
    with tempfile.TemporaryDirectory(prefix='lekiwi-apt-') as tmp:
        temp = Path(tmp)
        with urllib.request.urlopen(key_url, timeout=30) as r:
            data = r.read(1024*1024)
        if not data.startswith(b'-----BEGIN PGP PUBLIC KEY BLOCK-----'):
            raise RuntimeError('APT 서명 키 응답 형식이 올바르지 않습니다.')
        (temp/'key').write_bytes(data)
        (temp/'source').write_text(source+'\n')
        run(['install', '-d', '-m', '0755', '/etc/apt/keyrings'], admin=True)
        run(['install', '-m', '0644', temp/'key', key], admin=True)
        run(['install', '-m', '0644', temp/'source', dest], admin=True)


def docker_command():
    # 원격 Docker/다른 사용자 daemon을 이 PC의 설치 대상으로 오인하지 않는다.
    if os.environ.get('DOCKER_HOST') or os.environ.get('DOCKER_CONTEXT'):
        raise RuntimeError('DOCKER_HOST/DOCKER_CONTEXT를 해제하고 로컬 Docker Engine에서 실행하세요.')
    context = query(['docker', 'context', 'show'])
    if context != 'default':
        raise RuntimeError('로컬 기본 Docker context만 지원합니다. 기존 context는 변경하지 않습니다.')
    endpoint = query(['docker', 'context', 'inspect', 'default', '--format', '{{.Endpoints.docker.Host}}'])
    if endpoint != 'unix:///var/run/docker.sock':
        raise RuntimeError('기본 Docker context가 시스템 로컬 소켓을 가리키지 않습니다. 설정을 변경하지 않습니다.')
    if query(['docker', 'info', '--format', '{{.ServerVersion}}']):
        return ['docker']
    run(['sudo', '-v'])
    if query(['sudo', '-n', 'docker', 'info', '--format', '{{.ServerVersion}}']):
        return ['sudo', 'docker']
    confirm('로컬 Docker 서비스가 응답하지 않습니다. systemctl start docker를 실행합니다.')
    run(['systemctl', 'start', 'docker'], admin=True)
    if not query(['sudo', '-n', 'docker', 'info', '--format', '{{.ServerVersion}}']):
        raise RuntimeError('Docker 서비스 시작 후에도 연결되지 않습니다.')
    return ['sudo', 'docker']


def install_host(info):
    helpers = [p for p in ('ca-certificates', 'curl', 'gnupg', 'xauth', 'util-linux')
               if query(['dpkg-query', '-W', '-f=${db:Status-Status}', p]) != 'installed']
    if helpers or not info['docker'] or not info['toolkit']:
        confirm('부족한 PC 준비 패키지와 Docker/NVIDIA Container Toolkit을 설치합니다.\n'
                '기존 Docker 저장 데이터와 사용자 설정은 보존합니다. 호스트 CUDA Toolkit은 설치하지 않습니다.')
        run(['apt-get', 'update'], admin=True)
    if helpers:
        run(['apt-get', 'install', '--no-remove', *helpers], admin=True)
    if not info['docker']:
        conflicts = [p for p in ('docker.io', 'podman-docker', 'containerd', 'runc', 'docker-desktop')
                     if query(['dpkg-query', '-W', '-f=${db:Status-Status}', p]) == 'installed']
        if conflicts:
            raise RuntimeError('기존 컨테이너 패키지는 자동 삭제하지 않습니다: '+', '.join(conflicts))
        install_source('lekiwi-docker', 'https://download.docker.com/linux/ubuntu/gpg',
                       'deb [arch=amd64 signed-by=/etc/apt/keyrings/lekiwi-docker.asc] '
                       f"https://download.docker.com/linux/ubuntu {info['codename']} stable")
        run(['apt-get', 'update'], admin=True)
        run(['apt-get', 'install', '--no-remove', 'docker-ce', 'docker-ce-cli', 'containerd.io',
             'docker-buildx-plugin', 'docker-compose-plugin'], admin=True)
    plugins = []
    ubuntu_docker = query(['dpkg-query', '-W', '-f=${db:Status-Status}', 'docker.io']) == 'installed'
    if version(query(['docker', 'compose', 'version', '--short'])) < (2, 30, 0):
        plugins.append('docker-compose-v2' if ubuntu_docker else 'docker-compose-plugin')
    if not query(['docker', 'buildx', 'version']):
        plugins.append('docker-buildx' if ubuntu_docker else 'docker-buildx-plugin')
    if plugins:
        confirm('기존 Docker의 부족한 플러그인을 준비합니다: '+', '.join(plugins))
        run(['apt-get', 'update'], admin=True)
        run(['apt-get', 'install', '--no-remove', *plugins], admin=True)
        if version(query(['docker', 'compose', 'version', '--short'])) < (2, 30, 0) or not query(['docker', 'buildx', 'version']):
            raise RuntimeError('저장소의 플러그인 버전이 부족합니다. Docker 공식 설치 안내로 갱신하세요. 기존 Engine은 자동 교체하지 않습니다.')
    docker = docker_command()
    if not info['toolkit']:
        install_source('lekiwi-nvidia-container', 'https://nvidia.github.io/libnvidia-container/gpgkey',
                       'deb [signed-by=/etc/apt/keyrings/lekiwi-nvidia-container.asc] '
                       'https://nvidia.github.io/libnvidia-container/stable/deb/amd64 /')
        run(['apt-get', 'update'], admin=True)
        run(['apt-get', 'install', '--no-remove', 'nvidia-container-toolkit'], admin=True)
    runtimes = docker_query(docker, ['info', '--format', '{{json .Runtimes}}'])
    if 'nvidia' not in json.loads(runtimes):
        running = docker_query(docker, ['ps', '-q'])
        if running:
            raise RuntimeError('실행 중인 컨테이너가 있어 Docker를 재시작하지 않습니다. 해당 작업을 정상 종료하고 다시 실행하세요.')
        confirm('Docker에 NVIDIA 런타임을 추가하고 Docker를 재시작합니다. 기존 daemon.json은 먼저 백업합니다.')
        backup = '/etc/docker/daemon.json.lekiwi-'+str(time.time_ns())+'.bak'
        run(['install', '-d', '-m', '0755', '/etc/docker'], admin=True)
        if subprocess.run(['sudo', 'test', '-f', '/etc/docker/daemon.json']).returncode == 0:
            run(['cp', '-a', '/etc/docker/daemon.json', backup], admin=True)
        run(['nvidia-ctk', 'runtime', 'configure', '--runtime=docker'], admin=True)
        run(['systemctl', 'restart', 'docker'], admin=True)
    return docker


def project_env(docker):
    env = dict(os.environ, LEKIWI_DOCKER_SUDO='1' if docker[0] == 'sudo' else '0',
               LEKIWI_CAMERA_CONFIG='', LEKIWI_TELEOP_STATE='', LEKIWI_TELEOP_SESSION='')
    return env


def verify(docker):
    if os.environ.get('ACCEPT_EULA') != 'Y':
        raise RuntimeError('NVIDIA 라이선스를 읽고 동의한 경우 ACCEPT_EULA=Y를 설정한 뒤 다시 실행하세요. docs/student-setup.md 참고.')
    env = project_env(docker)
    # 검증 명령이 뜻하지 않게 큰 이미지를 빌드하는 것을 방지한다.
    compose = docker+['compose', '--project-directory', str(ROOT), '-f', str(ROOT/'compose.yaml')]
    result = subprocess.run(compose+['config', '--images'], env=env, text=True, capture_output=True, check=True)
    for image in result.stdout.splitlines():
        if not query(docker+['image', 'inspect', '--format', '{{.Id}}', image]):
            raise RuntimeError(f'검사 이미지가 없습니다: {image}. ./lekiwi install로 이미지를 먼저 준비하세요.')
    run([ROOT/'lekiwi', 'check-ml'], env=env)
    run([ROOT/'lekiwi', 'test-cameras'], env=env)
    print('LEKIWI_INSTALL verification=PASS: CUDA 계산·LeKiwi 두 카메라·짧은 기록 검사 통과. GUI와 긴 실습은 별도 확인하세요.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='환경과 설치 계획만 표시. sudo·다운로드·변경 없음')
    mode.add_argument('--verify', action='store_true', help='기존 Docker 이미지로 CUDA·카메라·기록 검사')
    args = p.parse_args()
    info = inspect(ROOT)
    result = assess(info)
    print(json.dumps({k: v for k, v in info.items() if k != 'driver_devices'}, ensure_ascii=False, indent=2))
    for msg in result['warnings']:
        print('안내: '+msg)
    print('계획: '+('현재 드라이버 유지' if result['driver_ready'] else 'GPU 지원 후보 중 580 계열 드라이버 설치')+
          ' → Docker·Container Toolkit 준비 → 이미지 빌드 → CUDA·카메라·기록 검사')
    if result['errors']:
        raise RuntimeError('\n'.join(result['errors']))
    if args.check:
        print('LEKIWI_INSTALL check=PASS (설치 가능성 검사이며 실행 성공 판정은 아님)')
        return
    if os.geteuid() == 0:
        raise RuntimeError('전체 도구를 sudo로 실행하지 마세요. 필요한 명령만 sudo로 요청합니다.')
    if os.environ.get('DOCKER_HOST') or os.environ.get('DOCKER_CONTEXT') or (info['docker'] and query(['docker', 'context', 'show']) != 'default'):
        raise RuntimeError('자동 설치는 로컬 기본 Docker Engine만 지원합니다. 원격·Desktop·rootless context 설정은 변경하지 않습니다.')
    if info['docker'] and query(['docker', 'context', 'inspect', 'default', '--format', '{{.Endpoints.docker.Host}}']) != 'unix:///var/run/docker.sock':
        raise RuntimeError('기본 Docker context가 시스템 로컬 소켓을 가리키지 않습니다. 설치를 시작하지 않습니다.')
    reboot_gate(json.loads(read(state_path()) or '{}'), read('/proc/sys/kernel/random/boot_id'), result['driver_ready'])
    if args.verify:
        if not result['driver_ready']:
            raise RuntimeError('580 계열(580.65.06 이상) 드라이버가 필요합니다. ./lekiwi install을 먼저 실행하세요.')
        verify(docker_command())
        return
    if Path('/var/run/reboot-required').exists():
        raise RuntimeError('운영체제가 재부팅을 요청하고 있습니다. 작업 저장 후 재부팅하고 다시 실행하세요. 기존 환경 검사만 하려면 --verify를 사용하세요.')
    install_driver(info)
    # 드라이버가 준비된 이후에만 컨테이너 설치로 넘어간다.
    docker = install_host(info)
    save_state({'host_ready': True})
    if os.environ.get('ACCEPT_EULA') != 'Y':
        raise RuntimeError('PC 준비 완료. NVIDIA 라이선스 동의 후 ACCEPT_EULA=Y ./lekiwi install을 실행하면 이미지 준비를 계속합니다.')
    confirm('프로젝트의 Isaac Sim·LeRobot 이미지를 빌드하고 짧은 GPU 검사를 실행합니다. 최초 다운로드는 오래 걸릴 수 있습니다.')
    run([ROOT/'lekiwi', 'setup', 'all'], env=project_env(docker))
    verify(docker)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.SubprocessError, ValueError) as exc:
        print('중단: '+str(exc), file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print('\n사용자가 중단했습니다. 완료된 단계는 다음 실행에서 다시 확인합니다.', file=sys.stderr)
        sys.exit(130)
