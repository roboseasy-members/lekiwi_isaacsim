# 학생 PC 설치와 실행 확인

Ubuntu 22.04/24.04 x86_64의 로컬 NVIDIA GPU PC용입니다. 설치 도구는 Ubuntu 기본 `/usr/bin/python3`와 표준 라이브러리만 사용합니다. 실습 코드는 Docker에서 실행합니다.
Windows·WSL·macOS·ARM, 원격 Docker·Docker Desktop·rootless Docker의 자동 설정은 지원하지 않습니다.

## 처음 실행

Git이 없다면 먼저 `sudo apt update`와 `sudo apt install git`을 실행하고 저장소를 받습니다.
로보시지 멤버스의 공개 수업 저장소를 사용하므로 다운로드에 GitHub 로그인은 필요하지 않습니다.

```bash
git clone --branch develop https://github.com/roboseasy-members/lekiwi_isaacsim.git
cd lekiwi_isaacsim
./lekiwi install --check
```

`--check`는 GPU·OS·메모리·드라이버·Compose·Container Toolkit과 설치 계획을 출력합니다.
sudo, 네트워크 다운로드, 패키지 설치, 파일 쓰기 또는 GPU 프로그램 실행은 하지 않습니다.
`check=PASS`는 준비 절차를 진행할 수 있다는 뜻이며, 드라이버 후보 존재나 실습 성공을 보장하지 않습니다.
드라이버가 없으면 PCI 장치를 통해 GPU를 찾고 VRAM·정확한 이름은 드라이버 설치 후 확인합니다.

[NVIDIA 라이선스](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-software-license-agreement/)와
[Isaac Sim 컨테이너 안내](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/install_container.html)를 읽고 동의한 경우:

```bash
export ACCEPT_EULA=Y
./lekiwi install
```

전체 명령을 `sudo ./lekiwi install`로 실행하지 않습니다. 설치할 항목이 있으면 도구가 계획을 보여주고 `y` 입력과 필요한 sudo 인증을 요청합니다. APT·Secure Boot에서 추가 확인이 나올 수 있습니다. 비밀번호를 파일이나 환경 변수에 넣지 않습니다.

## 설치 흐름과 드라이버 선택

1. **환경 검사:** 지원 OS·NVIDIA PCI 장치를 확인합니다. RAM 32GB·VRAM 16GB 미달은 안내만 하고 설치를 허용합니다. GPU 이름으로 RTX 여부가 확인되어도 RTX 4080 수준의 성능을 충족했다고 판정하지 않습니다.
2. **드라이버 준비:** 모든 GPU에서 `nvidia-smi`가 동작하고 **580 계열이며 580.65.06 이상**이면 기존 드라이버를 유지합니다. 590·595 등 더 높은 계열도 준비 완료로 판정하지 않고, 지원되는 580 후보를 확인한 뒤 동의받아 교체합니다. 이는 프로젝트의 설치 정책이며 모든 GPU의 실행 성공을 보장하지 않습니다.
3. **설치가 필요한 경우:** Ubuntu의 `ubuntu-drivers devices`가 해당 GPU에 지원한다고 보고한 후보 중 **580 계열**을 선택합니다. 여러 GPU는 후보 교집합을 사용합니다. 가능한 경우 `580-open`, 아니면 `580`을 선택합니다. 선택한 패키지의 정확한 버전과 현재 커널의 `linux-headers`를 APT 모의 설치로 먼저 확인한 뒤, 동의받아 `apt-get install`로 설치합니다. 의존성이나 커널 헤더 후보를 해결하지 못하면 실제 드라이버 교체 전에 중단합니다. DKMS 모듈 빌드·서명 처리는 Ubuntu 패키지가 담당하며 빌드 실패 시에도 중단합니다.
4. **재부팅:** 교체 전 작업을 저장하고 Isaac Sim·학습 등 GPU 작업을 종료합니다. 설치 후 자동 재부팅하지 않습니다. 직접 재부팅한 뒤 같은 명령을 실행합니다. Secure Boot가 켜져 있으면 MOK 등록 화면을 완료해야 할 수 있습니다. 재실행 시 실제 로드된 버전이 580 계열인지 확인하며, 여전히 다른 계열이거나 GPU를 읽지 못하면 반복 설치하지 않고 원인 확인을 안내합니다.
5. **Docker 준비:** 필요한 보조 패키지, Docker Engine·Compose 2.30 이상·Buildx, NVIDIA Container Toolkit을 준비합니다. 기존 Docker Engine은 유지하며 부족한 플러그인을 해당 설치 계열로 준비합니다.
6. **GPU 런타임:** NVIDIA 런타임이 없으면 기존 `/etc/docker/daemon.json`을 같은 폴더에 시간별 `.bak` 파일로 백업하고 `nvidia-ctk runtime configure --runtime=docker`를 실행합니다. 실행 중인 컨테이너가 있으면 재시작 전에 중단하고 정상 종료를 안내합니다. 설정 반영에는 Docker 재시작이 필요합니다.
7. **이미지와 검사:** 프로젝트의 Isaac Sim·LeRobot 이미지를 빌드하고 CUDA 계산, 실제 LeKiwi 코스의 두 RGB와 60프레임 저장을 검사합니다.

GPU 드라이버와 NVIDIA Container Toolkit은 **PC에**, Isaac Sim·PyTorch·CUDA 라이브러리는 **Docker 이미지에** 설치합니다. 호스트 CUDA Toolkit은 설치하지 않습니다.
이미 준비된 드라이버·패키지·NVIDIA 런타임은 재설치하지 않습니다. 이미지 빌드는 Docker 캐시를 사용합니다. 다른 패키지 전체 업그레이드, 자동 재부팅, 사용자 Docker 그룹 추가, 기존 패키지 강제 제거는 하지 않습니다.

580은 현재 프로젝트의 자동 설치 정책이며 모든 미래 GPU를 지원한다는 뜻은 아닙니다. 후보가 없거나 다른 계열로 전환되는 패키지이면 자동 설치를 중단합니다. 강사가 GPU·Isaac Sim·드라이버 조합을 검증한 뒤 정책을 갱신해야 합니다. 단순히 최신 추천 계열이나 가장 큰 버전 번호를 선택하지 않습니다.
`.run`으로 설치한 기존 드라이버와 APT 설치는 자동 혼합하지 않습니다. 이미 NVIDIA 모듈이 로드됐는데 GPU를 읽지 못하는 경우도 드라이버를 무조건 교체하지 않습니다.

## 사양이 낮은 PC의 판정

| 상황 | 동작 |
|---|---|
| RAM·VRAM이 공식 최소보다 적음 | 안내 후 설치와 실행 검사 허용 |
| 드라이버가 없거나 580.65.06 미만, 또는 595 등 다른 계열 | 지원되는 580 후보를 조사하고 설치·교체 확인 요청 |
| 이름으로 확인된 GTX·A100·H100 등 RT 미지원 GPU | Isaac Sim 설치 절차 중단 |
| GPU 모델의 RT 지원 여부를 이름으로 판정하지 못함 | 알 수 없다고 표시하고 실제 렌더링 검사 수행 |
| NVIDIA GPU가 없거나 지원 범위 밖의 OS | 자동 설치 중단 |
| 기존 드라이버에서 렌더링 실패 | 실패 로그 안내. 드라이버 제거·교체를 자동 반복하지 않음 |

`nvidia-smi`에 나오는 CUDA Version은 호스트에 설치된 CUDA Toolkit 버전을 뜻하지 않습니다.
현재 RTX 5060 Laptop 약8GB·RAM 약15GiB PC처럼 공식 사양보다 낮아도 교육용 장면 실행이 가능할 수 있습니다. 다른 PC의 성능이나 학습까지 보장하는 기준으로 사용하지 않습니다.

## 준비 후 다시 검사

```bash
export ACCEPT_EULA=Y
./lekiwi install --verify
```

이 명령은 기존 이미지를 사용합니다. 이미지가 없으면 설치 명령으로 안내합니다. Isaac Sim은 창 없이 실행하고 종료하며 USB 리더에 연결하지 않습니다. 호스트 드라이버와 패키지는 설치하지 않습니다. Docker가 정지되어 있으면 서비스 시작을 확인할 수 있습니다.
`--verify`도 580 계열(580.65.06 이상)을 요구합니다. 다른 계열이면 검사 실행 전에 `./lekiwi install`로 안내합니다.

기존 설치 중 카메라 검사에서 실패했다면 저장소 폴더에서 최신 develop을 받은 뒤 이어서 진행합니다.

```bash
git pull --ff-only origin develop
export ACCEPT_EULA=Y
./lekiwi install
```

580 교체 후 재부팅 안내가 나오면 재부팅하고 마지막 두 명령을 다시 실행합니다. 설치 도구가 시스템 전체 업데이트를 고정하거나 차단하지는 않으므로, 나중에 OS 업데이트로 드라이버 계열이 바뀌면 다시 검사해야 합니다.

- CUDA: LeRobot 컨테이너에서 실제 GPU 텐서 연산을 검사합니다.
- 카메라: 실제 로봇·코스와 기본 TF에서 전방·손목 640×480 영상을 생성합니다.
- 기록: 30Hz의 60프레임을 저장하고 모든 원본 이미지의 무결성·시간 대응을 검사합니다.
- 결과: `data/setup/camera-check.*/report.json`, `front.png`, `wrist.png`, 짧은 원본 기록과 코스가 남습니다.
- 로그: `data/logs/sim/check.*.log`. 드라이버 재부팅 상태는 `data/setup/host-state.json`에 남습니다. 모두 Git에서 제외됩니다.

`verification=PASS`는 **이 짧은 검사 통과**를 뜻합니다. GUI 첫 실행은 아래처럼 별도로 확인합니다.

```bash
# Docker에 sudo가 필요한 PC에서만
export LEKIWI_DOCKER_SUDO=1
./lekiwi record
```

두 미리보기와 기본 조작을 확인하고 짧은 기록을 저장합니다. 긴 수집·실제 리더·학습의 속도와 메모리는 각 실습에서 확인합니다. 설치 도구는 카메라 해상도나 학습 배치 크기를 임의로 바꾸지 않습니다.

## 파일 역할과 근거

- `tools/host_setup/checks.py`: 읽기 전용 하드웨어 조사와 드라이버 선택 정책.
- `tools/host_setup/main.py`: 설치·재부팅 안내·기존 시스템 보존·검사 순서.
- `isaac_sim/camera_smoke_test.py`: Docker 안의 실제 GPU 카메라·기록 검사.
- `tests/test_host_setup.py`: 패키지 설치 없이 정책·실패 분기 검사.

[Ubuntu 드라이버 설치](https://ubuntu.com/server/docs/how-to/graphics/install-nvidia-drivers/),
[Docker Ubuntu 설치](https://docs.docker.com/engine/install/ubuntu/),
[NVIDIA Container Toolkit 설치](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html),
[Isaac Sim 5.1 요구사항](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/requirements.html)를 바탕으로 구성했습니다.
Ubuntu 권장 패키지 관리와 공식 Docker/NVIDIA 저장소를 사용하며, 프로젝트에서 확인한 580 계열과 낮은 사양 허용 정책은 이 저장소의 선택입니다.

## 제작 PC 검증 · 2026-09-08

- Ubuntu 24.04, RTX 5060 Laptop 8GB, OS RAM 약14.9GiB, 드라이버 580.173.02에서 `install --check`가 메모리 부족 안내 후 기존 드라이버 유지를 선택했습니다.
- `install --verify`에서 LeRobot CUDA 연산과 실제 Docker LeKiwi 코스의 전방·손목 영상, 60프레임·120개 RGB 기록 검사를 통과했습니다. 두 샘플 영상도 직접 확인했습니다.
- 2026-09-09 기준 호스트 전체 자동 검사 314개 통과, 호스트에 USD Python(`pxr`)이 없어 8개 생략. 설치 도구 검사 50개에서 595 → 580 교체 분기, 모의 설치 실패 시 중단, 재부팅 후 실제 버전 확인, 낮은 사양 허용, 후보 교집합, 원격 Docker 차단과 기존 환경 보존을 확인했습니다. 드라이버 교체 명령은 모의 검사이며 개발 PC의 드라이버는 변경하지 않았습니다.
- 두 Docker 이미지 빌드와 문서·교재 링크·39개 원본/주석 이미지·6개 ZIP 검사를 수행했습니다.
- 이 PC의 드라이버·APT 패키지·Docker 런타임 설정을 교체하지 않았습니다. **깨끗한 별도 Ubuntu PC에서 드라이버 신규 설치와 Secure Boot 재부팅 전체 과정은 아직 실물 검증하지 않았습니다.** 수업 배포 전 대표 PC에서 해당 경로를 추가 확인해야 합니다.
