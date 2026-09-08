# LeKiwi Isaac Sim · Teleop과 기초 교육자료

실제 **SO101 리더암 + 키보드**로 Isaac Sim 안의 **LeKiwi 모바일 베이스 + SO101 팔**을 조작합니다.
원형·십자 도로에서 블록에 접근하고 집어서 바구니까지 운반하는 teleop 환경입니다.

**URDF·USD·mesh가 저장소에 포함되어 있으므로 로봇 자산을 따로 다운로드하지 않습니다.**
호스트에 Isaac Sim·Python·LeRobot·ROS·Conda를 설치하지 않고 Docker 이미지 안에서 실행합니다.
단, NVIDIA 드라이버와 Docker 실행 기반은 PC에 먼저 설치해야 합니다.

## 현재 구현 범위

객체 물리·관절·카메라·조작·기초 데이터 기록을 1~5편 순서로 배우려면 [Isaac Sim Basic 교육자료](isaacsim_basic/README.md)를 사용하세요.
`./lekiwi setup sim` 후 `./lekiwi basic`으로 Docker 안의 별도 기초 실습을 시작합니다.
5편은 `./lekiwi basic --lesson recording`으로 시작하며, 한 관절의 상태·명령 JSON을 저장·재생합니다.
각 편의 폴더에는 교재 MD, 실습 기록지, 실제 스크린샷과 빨간 표시, 노션 가져오기용 ZIP이 있습니다.

| 편 | 교육자료 | 주요 실습 |
|---|---|---|
| 1 | [객체와 물리 성질](isaacsim_basic/01_object_physics/README.md) | 객체 생성, Collider, 질량·중력, 마찰·반발력 |
| 2 | [로봇과 관절](isaacsim_basic/02_robot_joints/README.md) | 관절 축·한계와 Drive 설정 |
| 3 | [전방·손목 카메라](isaacsim_basic/03_robot_cameras/README.md) | 시점 전환, 장착 좌표, 화각 |
| 4 | [원격 조작](isaacsim_basic/04_teleoperation/README.md) | 키보드 주행과 SO101 리더 조작 |
| 5 | [기초 데이터 기록](isaacsim_basic/05_data_recording/README.md) | 한 관절의 에피소드 기록·저장·재생 |

1·2편은 기본 Stage·Property 창을 사용합니다. 3·4편의 조작 창과 5편의 기록 창은
실행 시 **Stage 옆 탭에 자동 배치**됩니다. 객체 목록은 Stage 탭, 조작 안내는 해당 실습 탭에서 확인합니다.

- 키보드 베이스 주행, SO101 리더 calibration/재사용, 가상 팔의 리더 자세 추종.
- 중앙에서 시작하는 LeKiwi, 바깥 원형 도로 + 안쪽 십자 도로, 위치·회전 방향이 랜덤인 네 블록과 고정 바구니.
- 생성된 초기 배치 저장과 재현, 화면 캡처.
- 전방 구멍·손목의 임시 카메라 장착과 시점 전환. 실제 TF 측정 후 위치·방향 보정 예정.
- 개발 PC에서 사용자가 통합 teleop과 코스 화면을 확인했습니다. 다른 PC/리더에서는 별도 검증이 필요합니다.
- **아직 없음:** 카메라 동기화, LeRobot 데이터셋 녹화, 실행 중 에피소드 리셋, 자동 성공 판정, 학습 정책 실행.

ACT/GR00T 의존성과 학습 CLI는 준비되어 있지만, 이 로봇의 수집→학습→평가 전 과정은 아직 구현·검증하지 않았습니다.
통합 teleop은 직접 조작하는 환경이며, 실행만으로 데이터셋이 기록되지는 않습니다.
5편은 에피소드의 구조를 배우는 한 관절 JSON 실습입니다.
LeKiwi의 전방·손목 영상과 팔·베이스 명령을 함께 모으는 본격적인 데이터 수집은 후속 과정입니다.
실제 follower나 실제 LeKiwi 베이스를 움직이는 기능도 없습니다.

## 브랜치 안내

| 브랜치 | 역할 |
|---|---|
| `main` | 최종 안정 버전 |
| `develop` | 기존 teleop을 포함하고 기능별 PR을 통합하는 개발 브랜치 |
| `feature/isaacsim_basic` | 기존 teleop에 카메라·기초 교육자료 1~5편과 실습 창 자동 배치를 추가한 작업 브랜치 |

기존 teleop 작업은 `develop`에 통합했습니다. 새 기능은 `feature/기능명`에서 작업하고 PR로 `develop`에 통합합니다.
`feature/isaacsim_basic`에는 기존 teleop과 이후 추가한 교육자료가 함께 포함되어 있습니다.
현재 교육자료를 사용하려면 아래처럼 `feature/isaacsim_basic`을 받으세요.

## 1. 처음 한 번: PC 준비

이 안내는 **Ubuntu 22.04/24.04, Linux x86_64, 로컬 데스크톱** 기준입니다.
Windows/WSL/macOS, 원격 SSH 화면, ARM PC는 이 프로젝트에서 검증하지 않았습니다.

1. NVIDIA GPU와 호환 드라이버를 설치하고 아래 명령으로 확인합니다.
   [Isaac Sim 5.1 공식 요구사항](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/requirements.html)을 먼저 확인하세요.
   공식 최소 사양에는 RAM 32 GB·VRAM 16 GB가 명시되어 있습니다.
   개발 PC의 RTX 5060 Laptop 8 GB에서도 현재 코스를 실행했지만 공식 최소 VRAM보다 작고,
   화면 멈춤 이력도 있어 모든 PC에서 안정적인 실행을 보장하지 않습니다.

~~~bash
nvidia-smi
~~~

2. [Docker Ubuntu 설치 안내](https://docs.docker.com/engine/install/ubuntu/)에 따라
   Docker Engine, Buildx, Compose 플러그인을 설치합니다. Compose는 2.30 이상을 사용합니다.
   Docker가 이미 설치되어 있으면 기존 컨테이너나 데이터를 삭제하지 말고 버전을 확인하세요.
3. [NVIDIA Container Toolkit 설치 안내](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)에 따라
   Toolkit을 설치하고 해당 문서의 Docker 런타임 설정까지 진행합니다.
   **Docker 재시작은 다른 컨테이너에도 영향을 줍니다. 기존 작업이 있을 때는 먼저 안전하게 종료하세요.**
4. Ubuntu 터미널에서 보조 도구를 설치합니다.

~~~bash
sudo apt update
sudo apt install -y git xauth util-linux
~~~

설치 후 다음 명령이 정상 출력되는지 확인합니다.

~~~bash
docker compose version
sudo docker info
echo "$DISPLAY"
~~~

DISPLAY는 로컬 데스크톱에서 보통 :0 또는 :1입니다. 비어 있으면 Ubuntu 데스크톱의 터미널에서 진행하세요.
GUI에는 X11 또는 XWayland와 xauth가 필요합니다. 호스트 CUDA Toolkit 설치는 필요하지 않습니다.
최초 이미지 빌드에는 인터넷과 이미지·캐시를 저장할 충분한 여유 디스크 공간이 필요합니다.

## 2. 저장소 받기

비공개 저장소인 경우 소유자가 접근 권한을 부여해야 하며 GitHub 인증도 필요합니다.
HTTPS 인증 요청에는 GitHub 비밀번호가 아닌 GitHub CLI/자격 증명 관리자의 인증을 사용하세요.
이미 GitHub CLI로 로그인했다면 해당 인증을 사용할 수 있습니다.

~~~bash
git clone --branch feature/isaacsim_basic https://github.com/SJun99/lekiwi_isaacsim.git
cd lekiwi_isaacsim
~~~

이후 명령은 **이 폴더의 같은 터미널**에서 실행합니다.

아래는 Docker에 sudo가 필요한 PC를 기준으로 합니다.
sudo 없이 docker info가 성공하는 PC에서는 다음 export를 생략해도 됩니다.
스크립트 전체를 sudo로 실행하면 생성 파일의 소유자가 달라질 수 있으므로 sudo ./lekiwi 형태로 실행하지 마세요.

~~~bash
export LEKIWI_DOCKER_SUDO=1
~~~

[NVIDIA 라이선스](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-software-license-agreement/)와
[Isaac Sim 컨테이너 안내](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/install_container.html)를 읽고
동의한 경우에만 다음 값을 설정합니다.

~~~bash
export ACCEPT_EULA=Y
~~~

export는 현재 터미널에만 적용됩니다. 새 터미널에서는 다시 설정하세요.
라이선스 동의와 이미지·팔 설정은 .env.example을 .env로 복사해 편집할 수도 있습니다.
.env와 data/는 Git에 올라가지 않습니다.

## 3. Docker 이미지 만들기

~~~bash
./lekiwi doctor
./lekiwi setup all
./lekiwi validate
./lekiwi check-ml
~~~

기초 교육의 1~3편, 4편 키보드 실습, 5편만 진행한다면 `./lekiwi setup sim`으로 Isaac Sim 이미지만 빌드해도 됩니다.
실제 리더를 사용하는 4편 실습에는 LeRobot 이미지도 필요합니다.

- doctor: Docker 접근, GPU와 번들 자산 확인.
- setup all: Isaac Sim 이미지와 LeRobot/리더암 이미지 모두 빌드. 최초 다운로드·설치에는 시간이 걸립니다.
- validate: 로봇 파일과 mesh 경로 검사.
- check-ml: LeRobot 의존성과 CUDA 계산 검사. 리더 USB에는 연결하지 않습니다.

**현재 프로젝트 이미지는 공개 레지스트리에 배포하지 않았습니다.**
Git clone 후 setup all로 PC에서 이미지를 만드는 방식입니다.
이미지 이름은 lekiwi-sim:0.1.0과 lekiwi-lerobot:0.1.0입니다.
GitHub 코드 업데이트 후에는 setup all을 다시 실행해야 변경 코드가 이미지에 반영됩니다.
매 teleop 실행마다 빌드할 필요는 없습니다.

## 4. 리더 없이 환경부터 확인하기

~~~bash
./lekiwi scene
~~~

LeKiwi가 중앙에서 시작하고 네 블록과 네 바구니가 나타납니다.
첫 시작은 렌더링 캐시 준비로 느릴 수 있으니 같은 명령을 중복 실행하지 마세요.
이 명령에서는 키보드로 베이스만 조작하며 팔은 기본 자세로 유지합니다.

| 처음 전체 화면 방향 | 길·블록·바구니 색 |
|---|---|
| 위 (+X) | 빨강 |
| 아래 (-X) | 주황 |
| 왼쪽 (+Y) | 노랑 |
| 오른쪽 (-Y) | 초록 |

도로·길별 색·바구니는 고정이고 **각 길의 블록 1개씩, 총 4개의 위치와 바닥 위 회전 방향이 매번 랜덤**입니다.
작업 선택 창은 없습니다. 원하는 블록을 직접 집어 운반합니다.
블록 한 변은 4 cm이며, 바구니는 윗부분이 열려 있습니다.
원형 도로로도 다른 길에 접근할 수 있습니다.

확인이 끝나면 **Isaac 창을 닫고 종료될 때까지 기다린 뒤** 다음 단계로 갑니다.
시뮬레이터는 한 번에 하나만 실행할 수 있습니다.

## 5. SO101 리더 연결과 calibration

실제 SO101 **리더**에 하드웨어 안내에 맞는 전원과 데이터 USB를 연결합니다.
리더를 안정적으로 지지하고 전원을 즉시 차단할 수 있게 준비하세요.
실제 리더에는 토크 활성화·위치 이동 명령을 보내지 않지만,
연결·보정 과정에서 토크 해제와 모터 설정 기록이 있으므로 안전 확인을 건너뛰지 마세요.

~~~bash
ls -l /dev/serial/by-id/
~~~

출력에서 본인 리더의 경로를 복사합니다. 여러 장치가 있으면 추측하지 말고
리더 USB 분리/재연결 시 바뀌는 항목을 확인하세요.
아래 **usb-본인_SO101_장치**는 반드시 실제 이름으로 바꿉니다.

~~~bash
./lekiwi teleop \
  --port /dev/serial/by-id/usb-본인_SO101_장치 \
  --id so101_leader \
  --scene random
~~~

같은 리더는 --id 값을 계속 동일하게 유지합니다.
--scene random은 고정 도로에서 네 블록의 위치를 새로 생성합니다.
리더 안내는 실행 터미널에, 시뮬레이터 로그는 data/teleop/session.*/sim.log에 표시/저장됩니다.

### 처음 보정할 때

파일이 없으면 LeRobot 기본 보정 절차가 시작됩니다.
터미널의 **연결 안전 확인 → 중간 자세 → 관절 범위 측정** 안내를 한 단계씩 따르고,
각 단계가 끝나면 안내에 맞게 Enter를 누릅니다. 관절을 무리하게 비틀거나 한계 밖으로 밀지 마세요.

### 기존 보정이 있을 때

실행할 때마다 다음 선택이 나타납니다.

~~~text
Press ENTER to use provided calibration file associated with the id so101_leader, or type 'c' and press ENTER to run calibration:
~~~

- Enter: 기존 보정 사용.
- c + Enter: 다시 보정. 기존 파일은 백업.
- Ctrl+C: 취소.

리더를 받치고 전원 차단이 가능한지 묻는 별도 안내에서도 준비한 후 Enter를 누릅니다.
보정은 리더마다 다르므로 다른 사람의 파일을 그대로 쓰지 마세요.
저장 위치는 data/calibration/so101_leader/so101_leader.json입니다.

## 6. 활성화하고 조작하기

리더 준비 메시지와 시뮬레이터 화면이 모두 나온 뒤,
**로봇이 보이는 뷰포트를 클릭하고 R**을 누릅니다.
ACTIVE 표시를 확인하고 리더 관절을 조금씩 움직여 방향을 확인하세요.
통합 teleop에서는 R 활성화 전에는 베이스도 움직이지 않습니다.

| 키 | 동작 |
|---|---|
| R | 리더 자세 추종 활성화/재활성화 |
| W / S | 베이스 전진 / 후진 |
| A / D | 베이스 좌 / 우 평행이동 |
| Q / E | 베이스 반시계 / 시계 회전 |
| 1 | 기본 속도: 0.25 m/s, 0.8 rad/s |
| 2 | 기본의 1.5배 |
| 3 | 기본의 2배 |
| Space | 베이스 정지, 팔 목표 유지, teleop 비활성화 |
| T | 자유 시점 / 로봇 추적 시점 전환 |
| C | 전체 / 전방 카메라 / 손목 카메라 시점 전환 |
| P | 화면 캡처 저장 |

집기 연습은 속도 1로 접근한 뒤 베이스를 멈추고 리더로 팔·집게를 조작하세요.
Space로 정지했다면 팔을 조작하기 전에 R이 다시 필요합니다.
블록이 집혔는지 화면에서 확인한 뒤 운반합니다. 자동 부착이나 자동 집기는 없습니다.

집게가 양옆을 향하도록 손목 기본값에 -90° 보정이 적용되어 있습니다.
관절 한계로 인해 리더의 모든 자세를 복제할 수는 없습니다.
LIMIT는 관절 한계, STOP은 입력 누락/만료 등에 의한 비활성 상태입니다.
원인을 확인한 뒤에만 R로 다시 활성화하세요.

## 7. 종료와 다음 실행

Space로 정지한 뒤 **Isaac 창을 닫거나 실행 터미널에서 Ctrl+C**를 누릅니다.
이번 실행의 시뮬레이터·리더 컨테이너가 정리됩니다.
종료 로그의 Torque_Enable 값이 모두 0인지 확인하세요.
확인 실패가 나오면 장비 상태를 추측하지 마세요.

~~~bash
./lekiwi status
~~~

프로젝트 컨테이너가 모두 종료된 뒤 다음 실행을 시작합니다.
다음에는 5단계의 teleop 명령만 실행하면 됩니다. 이미지 재빌드나 보정 재측정은 매번 필요하지 않습니다.

GUI만 종료해야 할 때 ./lekiwi stop을 사용할 수 있습니다.
sudo를 사용하는 긴 세션에서는 인증 만료로 기존 터미널의 종료 처리가 비밀번호를 기다릴 수 있습니다.
**기존 실행 터미널을 확인하고, status에서 리더까지 종료됐는지 확인한 뒤** 다시 실행하세요.
새 세션을 중복 실행하거나 광범위한 프로세스 종료 명령을 사용하지 마세요.

## 배치 저장과 재현

매 실행의 seed·초기 블록 배치는 data/scenes/course.XXXXXXXX/layout.json에 저장됩니다.
course.usda는 같은 환경의 USD입니다. 조작 후 상태나 데이터셋 녹화본은 아닙니다.
로그의 LEKIWI_COURSE saved=...에서 실제 폴더명을 확인하세요.

~~~bash
# 같은 seed로 환경 미리보기
./lekiwi scene --seed 42

# XXXXXXXX와 USB 이름을 실제 값으로 변경: 저장한 초기 배치로 teleop
./lekiwi teleop \
  --port /dev/serial/by-id/usb-본인_SO101_장치 \
  --id so101_leader \
  --scene /data/scenes/course.XXXXXXXX/layout.json
~~~

저장 파일로 실행하면 블록 위치는 바뀌지 않습니다. 새 위치가 필요하면 --scene random을 사용합니다.
--scene의 파일 경로는 호스트 경로가 아니라 Docker 안의 /data/... 경로입니다.

## 문제가 생겼을 때

| 증상 | 먼저 확인할 것 |
|---|---|
| Docker 접근 오류 | 같은 터미널의 LEKIWI_DOCKER_SUDO=1 설정, Docker 서비스 |
| GPU를 못 찾음 | 호스트 nvidia-smi, NVIDIA Container Toolkit 설정 |
| 화면이 뜨지 않음 | 로컬 DISPLAY, xauth, 라이선스 동의, 해당 세션 sim.log |
| 이미 실행 중이라는 오류 | 기존 Isaac/실행 터미널 종료 후 ./lekiwi status |
| 리더 장치가 없음 | 데이터 USB 케이블, /dev/serial/by-id/ 경로 |
| R을 눌러도 반응 없음 | 터미널 보정/안전 확인 완료, 뷰포트 포커스, ACTIVE/STOP 상태 |
| 팔 방향이 반대 | 즉시 Space, [보정·관절 방향 설정](docs/so101-teleop.md) 확인 |
| 화면 멈춤 / Vulkan 오류 | 중복 실행 금지, sim.log와 nvidia-smi 확인; GPU/드라이버 문제일 수 있음 |
| 블록 위치가 항상 같음 | 고정 seed/저장 파일 대신 --scene random 사용 |

실행 터미널에 표시된 **해당 세션**의 로그를 확인하세요.
Docker 전체 정리나 보정 파일 삭제로 해결하려 하지 마세요.

## 저장 파일과 검증

data/는 호스트에 남으며 Git이나 Docker 이미지에 포함하지 않습니다.

~~~text
data/
├── calibration/  # 사용자 보정값과 백업
├── scenes/       # 초기 환경 배치
├── teleop/       # 실행별 상태와 sim.log
├── captures/     # 화면 캡처
├── isaacsim_basic/ # 기초 실습 장면과 5편 에피소드 JSON
├── datasets/     # 향후 데이터셋 공간 (현재 녹화 기능 없음)
├── outputs/      # 학습 출력
└── cache/, logs/, isaac-data/, home/  # 캐시·설정
~~~

다음 검사는 GUI/teleop을 모두 종료한 후 하나씩 실행하세요.
리더 USB를 사용하지 않으며 실제 집기 성공 검사를 대신하지 않습니다.

~~~bash
./lekiwi validate-usd
./lekiwi test-physics
./lekiwi test-arm
./lekiwi test-scene
./lekiwi test-basic
./lekiwi test-recording
~~~

`test-basic`은 기초 물리·관절 장면을, `test-recording`은 한 관절의 180프레임 기록·저장·재생을 검사합니다.

일반 사용자는 build-assets를 실행할 필요가 없습니다.
원본 CAD/ROS 작업 폴더 src/와 isaac_sim_bundle/은 배포에 필요하지 않아 저장소에 포함하지 않습니다.

## 학습과 개발 자료

이미 별도로 준비한 로컬 LeRobot 데이터셋이 있는 경우에만 다음처럼 학습 CLI를 사용할 수 있습니다.
이 로봇의 수집·학습·추론 성공을 보장하는 프리셋은 아직 없습니다.

~~~bash
./lekiwi train act \
  --dataset.repo_id=local/demo01 \
  --dataset.root=/data/datasets/demo01 \
  --output_dir=/data/outputs/act_demo01 \
  --batch_size=4 --steps=1000
~~~

train groot도 CLI에 연결되지만 가중치·로봇 동작 표현·GPU 메모리 요구사항을 별도로 확인해야 합니다.
사전학습 가중치는 번들 로봇 자산과 다르며 별도 다운로드가 필요할 수 있습니다.
Hub 업로드와 W&B는 기본 비활성입니다.

- [코스 상세와 Script Editor 예제](docs/collection-course.md)
- [SO101 보정·좌표·안전 제약](docs/so101-teleop.md)
- [Docker 구조와 후속 개발](docs/architecture.md)
- [모델·물리 설명](isaac_sim/README.md)
- [카메라 장착 위치와 추후 TF 반영](docs/robot-cameras.md)
- [자산 출처](isaac_sim/assets/lekiwi_soarm/SOURCE.md)
- [개발 PC 검증 이력](docs/validation-2026-09-07.md)

번들 mesh의 재배포 라이선스 확인 자료는 아직 완결되지 않았습니다.
저장소에 파일이 있다는 이유로 제3자 자산의 재배포 권리가 새로 부여되지는 않습니다.
NVIDIA 이미지·LeRobot·학습 가중치에는 각각의 라이선스가 적용됩니다.
