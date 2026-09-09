"""학생 PC의 읽기 전용 검사와 설치 정책. 시스템 변경은 수행하지 않는다."""
import csv
import os
import platform
from pathlib import Path
import re
import shutil
import subprocess

MIN_DRIVER = (580, 65, 6)
AUTO_DRIVER_BRANCH = '580'


def read(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return ''


def query(args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=30,
                           env=dict(os.environ, LC_ALL='C'))
        return r.stdout.strip() if r.returncode == 0 else ''
    except (OSError, subprocess.TimeoutExpired):
        return ''


def version(value):
    m = re.search(r'(\d+)\.(\d+)(?:\.(\d+))?', value)
    return tuple(int(v or 0) for v in m.groups()) if m else (0, 0, 0)


def parse_gpus(output):
    result = []
    for row in csv.reader(output.splitlines(), skipinitialspace=True):
        if len(row) != 3:
            continue
        try:
            result.append(dict(name=row[0], vram_mib=float(row[1]), driver=row[2]))
        except ValueError:
            continue
    return result


def rt_support(name):
    name = name.upper()
    if 'RTX' in name:
        return 'yes'
    if re.search(r'\b(GTX|GT|TESLA|A100|H100|H200|V100|P100|P40|T4|B100|B200)\b', name):
        return 'no'
    return 'unknown'


def driver_packages(output):
    """여러 NVIDIA GPU가 있으면 모든 장치의 지원 후보 교집합만 사용한다."""
    groups = []
    for block in re.split(r'^== .* ==$', output, flags=re.M):
        if 'v000010DE' not in block and 'NVIDIA' not in block:
            continue
        groups.append(set(re.findall(r'^driver\s*:\s*(nvidia-driver-\d+(?:-open)?)\s+-', block, re.M)))
    return set.intersection(*groups) if groups else set()


def select_driver(output, candidates):
    supported = driver_packages(output)
    for package in (f'nvidia-driver-{AUTO_DRIVER_BRANCH}-open', f'nvidia-driver-{AUTO_DRIVER_BRANCH}'):
        candidate = candidates.get(package, '')
        if package in supported and version(candidate) >= MIN_DRIVER and version(candidate)[0] == int(AUTO_DRIVER_BRANCH):
            return package
    return None


def inspect(root):
    release = dict(line.split('=', 1) for line in read('/etc/os-release').splitlines() if '=' in line)
    release = {k: v.strip('"') for k, v in release.items()}
    pci = []
    for path in Path('/sys/bus/pci/devices').glob('*'):
        if read(path/'vendor') == '0x10de' and read(path/'class').startswith('0x03'):
            pci.append(path.name)
    gpus = parse_gpus(query(['nvidia-smi', '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader,nounits']))
    mem = re.search(r'MemTotal:\s+(\d+)', read('/proc/meminfo'))
    return dict(os=release.get('ID'), release=release.get('VERSION_ID'),
                codename=release.get('VERSION_CODENAME'), arch=platform.machine(),
                kernel=platform.release(), pci=pci, gpus=gpus,
                ram_gib=int(mem[1])/1024**2 if mem else 0,
                free_gib=shutil.disk_usage(root).free/1024**3,
                cpu_threads=os.cpu_count() or 0,
                secure_boot=query(['mokutil', '--sb-state']) or '확인되지 않음',
                display=bool(os.environ.get('DISPLAY')),
                docker=bool(shutil.which('docker')),
                compose=query(['docker', 'compose', 'version', '--short']),
                toolkit=bool(shutil.which('nvidia-ctk')),
                driver_devices=query(['ubuntu-drivers', 'devices']))


def assess(info):
    errors, warnings = [], []
    if (info['os'], info['release'], info['arch']) not in {
            ('ubuntu', '22.04', 'x86_64'), ('ubuntu', '24.04', 'x86_64')}:
        errors.append('자동 설치 지원 범위는 Ubuntu 22.04/24.04 x86_64입니다.')
    if 'microsoft' in info['kernel'].lower():
        errors.append('WSL에서는 호스트 드라이버 설치를 지원하지 않습니다.')
    if not info['pci']:
        errors.append('PCI에서 NVIDIA GPU를 찾지 못했습니다.')
    if any(rt_support(g['name']) == 'no' for g in info['gpus']):
        errors.append('RT 미지원 GPU가 있습니다. 혼합 GPU 구성은 수동 장치 선택 후 검증해야 합니다.')
    if info['ram_gib'] < 30:
        warnings.append('RAM이 공식 32GB 기준보다 적습니다. 설치를 허용하며 실습 검사가 필요합니다.')
    if info['cpu_threads'] < 4:
        warnings.append('CPU 논리 프로세서가 4개 미만입니다. 실행 속도를 확인하세요.')
    if info['free_gib'] < 50:
        warnings.append('여유 공간이 50GiB 미만입니다. 이미지 빌드 중 공간이 부족할 수 있습니다.')
    for g in info['gpus']:
        if g['vram_mib'] < 15000:
            warnings.append(f"{g['name']}: 공식 VRAM 16GB 미달; 설치를 허용합니다.")
        if rt_support(g['name']) == 'unknown':
            warnings.append(f"{g['name']}: RT 지원 여부를 이름으로 판정하지 못했습니다. 렌더링 검사로 확인합니다.")
        if version(g['driver'])[0] != int(AUTO_DRIVER_BRANCH) and version(g['driver']) >= MIN_DRIVER:
            warnings.append(f"드라이버 {g['driver']}는 이 프로젝트의 검증 계열 580과 다릅니다. 유지 후 실제 검사를 수행합니다.")
    if not info['display']:
        warnings.append('DISPLAY가 없습니다. 자동 검사는 가능하지만 GUI 실습은 로컬 데스크톱에서 확인하세요.')
    ready = bool(info['gpus']) and len(info['gpus']) == len(info['pci']) and all(version(g['driver']) >= MIN_DRIVER for g in info['gpus'])
    return dict(errors=errors, warnings=warnings, driver_ready=ready)
