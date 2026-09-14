# LeKiwi Isaac Sim · 설치부터 로컬 데이터 수집까지

원격 수업 리허설은 **`develop`을 받아 [0장 환경 설정](isaacsim_basic/00_env_setting/README.md)부터 진행**합니다.
`develop`에는 0장 환경 설정, 1~6장 마우스·코드 실습과 원격 실습 기능이 통합되어 있습니다. 실제 수업 순서로 리허설을 마친 뒤 `main`에 반영합니다.
교육 흐름은 **환경 설정 → 기초 교육 → teleop → 로컬 데이터 수집·변환 → 로컬 학습 → 추론**입니다.
데이터셋은 로컬에서 사용하거나, 브라우저의 별도 스크립트로 Hugging Face에 공개 업로드할 수 있습니다.

실제 SO101 리더암과 키보드로 **Isaac Sim 안의 LeKiwi 베이스와 SOARM**을 조작합니다.
실제 follower나 실제 LeKiwi 본체를 움직이는 기능은 없습니다.
로봇 URDF·USD·mesh와 교재는 저장소에 포함되며, Isaac Sim·LeRobot은 Docker 안에서 실행합니다.

학생별 데스크탑과 Ubuntu 노트북을 서로 다른 망에서 연결할 때는
[0장 Tailscale 설정](isaacsim_basic/00_env_setting/README.md)을 따릅니다. 같은 LAN에서 접속하는 방법도 [원격 실습 안내](docs/remote-classroom.md)에 있습니다. 데스크탑이 시뮬레이션을 실행하고
노트북이 화면 수신·USB 리더암 입력을 담당합니다. 이 기능은 `develop`에서 제공하며,
아래의 한 PC 설치·실습 절차와 노트북 설치 절차를 구분합니다.

노트북에서 직접 코드를 바꾸며 수업할 때는 [브라우저 편집기 안내](docs/browser-classroom.md)를 사용합니다.
데스크탑의 `./lekiwi remote workspace --host 데스크탑IP`로 편집기를 켜고,
학생은 각 장 README를 읽고 WebRTC 화면에서 객체를 직접 만들며 실습합니다.
장 마지막의 코드 실습에서는 브라우저에서 Python을 저장한 뒤 `lesson run 1` / `lesson stop`으로 실행·종료합니다.

| 단계 | 이번 저장소에서 진행할 범위 |
|---|---|
| 1~3 · PC 준비 | 설치 도구와 개발 PC 실행 검사 준비. 새 PC의 드라이버 신규 설치·재부팅은 현장 검증 필요 |
| 4~8 · 교육·teleop·데이터 | 교재 1~6편, 리더 추종, 두 카메라 기록, 로컬 변환·검사 구현 |
| 9 · ACT 학습 | 학생 설정 스크립트와 공식 학습기 연결 구현. 검증 범위는 짧은 학습 실행까지 |
| 추론 | 저장한 ACT·정규화·카메라 설정으로 시뮬레이션 실행·정지·재시작 확인. 과제 성공률은 별도 평가 |

지원 설치 환경은 **Ubuntu 22.04/24.04 x86_64, 로컬 데스크톱, NVIDIA GPU**입니다.
Windows·WSL·macOS·ARM은 자동 설치 대상이 아닙니다.
RAM·VRAM이 공식 최소보다 적어도 경고 후 설치를 시도하지만 모든 GPU에서 실행을 보장하지 않습니다.
상세 조건은 [학생 PC 설치 안내](docs/student-setup.md)를 확인하세요.

<a id="2-저장소-받기"></a>

## 1. 새 PC에서 수업 브랜치 받기

Ubuntu 데스크톱의 터미널을 엽니다. Git이 없다면 먼저 설치합니다.

```bash
sudo apt update
sudo apt install git
```

저장소를 받을 위치에서 실행합니다. 비공개 저장소라면 GitHub 접근 권한과 인증을 먼저 준비합니다.

```bash
git clone --branch develop https://github.com/SJun99/lekiwi_isaacsim.git
cd lekiwi_isaacsim
git branch --show-current
```

**완료 기준:** 마지막 출력이 `develop`입니다. 이후 명령은 이 저장소 폴더에서 실행합니다.
clone만으로 드라이버나 프로그램이 자동 설치되지는 않습니다. 다음 단계의 설치 도구를 실행하세요.

<a id="1-처음-한-번-pc-준비"></a>

## 2. GPU·드라이버·Docker 준비

먼저 PC를 변경하지 않는 검사를 실행합니다.

```bash
./lekiwi install --check
```

`check=PASS`는 설치 절차를 시도할 수 있다는 뜻입니다. 실행 성공은 3단계에서 확인합니다.
오류가 나오면 [설치 안내의 지원 범위와 해결 절차](docs/student-setup.md)를 확인하고 다음 단계로 넘어가지 않습니다.

[NVIDIA 라이선스](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-software-license-agreement/)를 읽고 동의한 경우 아래를 실행합니다.

```bash
export ACCEPT_EULA=Y
./lekiwi install
```

설치 도구는 다음 순서로 진행하며 필요한 변경 전에 터미널에서 확인을 받습니다.

1. 모든 NVIDIA GPU에서 **580 계열이며 580.65.06 이상인 드라이버**가 로드되어 있으면 유지합니다. 드라이버가 없거나 범위 밖이면 GPU가 지원하는 580 계열 후보를 확인하고 동의 후 설치합니다. **595처럼 더 높은 계열도 그대로 사용하지 않고 580으로 교체합니다.** 지원 후보가 없으면 중단합니다.
2. 드라이버 설치로 재부팅이 필요하면 중단하고 안내합니다. 직접 작업을 저장하고 재부팅합니다. Secure Boot의 MOK 등록이 필요하면 화면 안내를 완료합니다.
3. Docker Engine·Compose·NVIDIA Container Toolkit을 준비합니다.
4. Isaac Sim·LeRobot 이미지를 빌드하고 CUDA·두 카메라·짧은 기록을 검사합니다.

재부팅한 경우 저장소 폴더로 돌아와 `export ACCEPT_EULA=Y`와 `./lekiwi install`을 다시 실행합니다.
재실행 시 실제 로드된 드라이버가 580 계열인지 확인한 뒤 Docker 준비와 카메라 검사로 넘어갑니다. 교체 전에는 작업을 저장하고 Isaac Sim·학습 등 GPU 작업을 종료하세요.
호스트 CUDA Toolkit·Conda·ROS를 따로 설치할 필요는 없습니다. 드라이버와 Docker 실행 기반은 PC에, 실습 의존성은 이미지에 설치합니다.
전체 명령을 `sudo ./lekiwi install`로 실행하지 마세요. 필요한 설치 작업만 도구가 sudo를 요청합니다.

**완료 기준:** `LEKIWI_INSTALL verification=PASS`가 출력됩니다. 설치 후보가 없거나 재부팅 후에도 실패하면 로그를 확인하고 강사에게 점검을 요청하세요.

## 3. 실행 권한과 첫 GUI 확인

설치 도구 안에서 선택한 Docker 권한은 현재 터미널에 자동 적용되지 않습니다.
다음 명령이 성공하는지 확인합니다.

```bash
docker info
```

권한 오류가 나오고 `sudo docker info`는 성공한다면, 아래 설정을 추가합니다.

```bash
export LEKIWI_DOCKER_SUDO=1
```

라이선스 동의 설정을 포함한 `export`는 새 터미널이나 재부팅 뒤 다시 적용해야 합니다.
이후 `./lekiwi` 전체를 sudo로 실행하지 않습니다.

```bash
export ACCEPT_EULA=Y
./lekiwi doctor
./lekiwi scene
```

**완료 기준:** 중앙의 LeKiwi, 원형·십자 도로, 네 블록과 네 바구니가 나타납니다.
블록 위치·회전은 무작위이며 키보드로 베이스를 조작할 수 있습니다. 이 실행에서 팔은 기본 자세를 유지합니다.
첫 실행은 캐시 준비로 느릴 수 있습니다. 같은 명령을 중복 실행하지 마세요.

확인 후 **Isaac Sim 창을 닫고 `./lekiwi status`로 종료를 확인**합니다.
설치 이후 GPU 검사를 다시 할 때만 `./lekiwi install --verify`를 사용합니다.
설치가 성공했다면 지금 `setup all`을 다시 실행할 필요는 없습니다.

## 4. 환경 설정과 기초 교육 0~6장 진행

[교재 전체 목차](isaacsim_basic/README.md)를 순서대로 따라갑니다.
각 장 README에서 **마우스로 객체 생성 → 속성 변경·Play 관찰 → 저장·정리 → 마지막에 코드 구현** 순서로 진행합니다.
스크린샷과 입력값이 같은 본문에 있으며, 기본 Stage·Property·Viewport를 사용합니다.
데스크탑의 첫 실습은 빈 편집 화면으로 시작합니다.

```bash
./lekiwi basic --script 01_object_physics/experiments/00_empty_stage.py
```

원격 수업에서는 0장의 접속 확인 후 1장 README의 빈 편집 화면 실행 명령을 사용합니다.
마지막 코드 절에서 `experiments/*.py`를 읽고 실행·수정합니다. 객체·물리·관절·카메라 설정 줄에는 한국어 설명과 단위가 있습니다.
코드 실습 실행은 `./lekiwi basic --chapter 1`부터 `--chapter 6`, 원격은 `lesson run 1`부터 `lesson run 6`입니다.
학생 파일을 저장한 뒤 재실행하면 반영되며, 코드 수정만으로 이미지 재빌드가 필요하지 않습니다.

| 편 | 내용 |
|---|---|
| 0 | 학생별 Tailscale 설정·브라우저와 영상 접속·Play 확인·결과 제출·공용 데스크탑 반납 |
| 1 | 객체·색상·중력·접촉·질량·마찰·반발 |
| 2 | 관절 축·제한·Drive 목표와 응답 |
| 3 | Camera API·화각·LeKiwi front/wrist TF |
| 4 | 키 입력·ArticulationAction·키보드 주행·선택 리더 실습 |
| 5 | 한 관절 JSON 기록·저장된 명령 재생 |
| 6 | LeKiwi 두 RGB·상태·명령 수집과 로컬 LeRobot 변환 |

0장은 준비 교재·실습 기록지·출처·노션 ZIP, 1~6편은 MD·학생 Python·실습 기록지·실제 화면·노션 ZIP을 포함합니다.
1~5장 API 예제는 일반 Isaac Sim 5.1 설치에서도 실행할 수 있습니다. 6장은 프로젝트 로봇·기록 모듈을 사용합니다.
기존 코드·리더 실습 기준의 계획 추정은 **2일 14~16시간**입니다. 직접 제작 시간을 포함한 일정은 리허설에서 다시 측정합니다. 설치·본격 시연 확보·학습은 별도입니다.
5장의 JSON은 에피소드 개념 예제이며 실제 로봇 학습 데이터는 6장에서 수집합니다.

## 5. SO101 리더 연결과 보정

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

## 6. Teleop 활성화와 조작

리더 준비 메시지와 시뮬레이터 화면이 모두 나온 뒤,
**로봇이 보이는 뷰포트를 클릭하고 R**을 누릅니다.
ACTIVE 표시를 확인하고 리더 관절을 조금씩 움직여 방향을 확인하세요.
통합 teleop에서는 R 활성화 전에는 베이스도 움직이지 않습니다.

시작 화면은 좌측 **Perspective**, 우측 **Front Camera**가 뷰포트 영역을 반씩 사용합니다.
`C`와 `T`는 좌측 시점을 변경하며 우측은 전방 카메라로 유지됩니다.

코스 반복 실습은 Viewport에서 **F8**을 누릅니다.
가상 로봇은 시작 자세로 돌아가고, 큐브는 각 색상의 라인 안에서 위치와 방향이 새로 정해집니다.
바구니와 도로는 유지되며 새 배치는 `data/scenes/course.*/layout.json`에 저장됩니다.
리셋 후에는 `R`을 다시 눌러 teleop을 활성화합니다. 실제 리더암 자세는 변경하지 않습니다.
녹화 중이거나 미저장 에피소드가 있으면 **F6 종료 → F7/F9 저장 또는 F10 두 번 폐기**를 완료한 후 리셋합니다.

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
| C | 좌측 화면: 전체 / 전방 카메라 / 손목 카메라 시점 전환 |
| P | 화면 캡처 저장 |

집기 연습은 속도 1로 접근한 뒤 베이스를 멈추고 리더로 팔·집게를 조작하세요.
손가락 두 곳은 안쪽 면을 보존하는 **Convex Decomposition** 충돌 형상을 사용합니다.
집게가 닫힌 뒤 큐브를 조금 들어 올려 유지되는지 확인하고 운반하세요.
가상 팔의 유지·회전·놓기는 `./lekiwi test-gripper`로 별도 검사할 수 있습니다(실물 USB 미사용).
Space로 정지했다면 팔을 조작하기 전에 R이 다시 필요합니다.
블록이 집혔는지 화면에서 확인한 뒤 운반합니다. 자동 부착이나 자동 집기는 없습니다.

집게가 양옆을 향하도록 손목 기본값에 -90° 보정이 적용되어 있습니다.
관절 한계로 인해 리더의 모든 자세를 복제할 수는 없습니다.
LIMIT는 관절 한계, STOP은 입력 누락/만료 등에 의한 비활성 상태입니다.
원인을 확인한 뒤에만 R로 다시 활성화하세요.

## 7. 로컬 데이터셋 취득

앞선 시뮬레이터가 종료된 상태에서 입력 방식 하나를 선택합니다.

**장비 없이 기록 경로를 먼저 확인할 때:**

```bash
./lekiwi record
```

이 모드는 키보드 베이스 조작을 기록하며 팔은 기본 자세를 유지합니다.
직진·정지 기록이 집기 학습 시연을 대신하지는 않습니다.

**리더로 팔과 베이스를 함께 시연할 때:** 5~6단계에서 확인한 USB 경로와 같은 리더 ID를 사용합니다.

```bash
./lekiwi teleop \
  --port /dev/serial/by-id/usb-본인_SO101_장치 \
  --id so101_leader \
  --scene random \
  --record
```

리더 안내를 완료하고 Viewport에서 R로 가상 팔 추종을 활성화합니다.
기록은 Viewport 단축키와 실행 터미널로 진행합니다.
시간은 실행 전에 `LEKIWI_RECORD_SECONDS=120`, 과제는 `LEKIWI_RECORD_TASK="Move a block to its matching basket"`로 지정하거나
6장 학생 파일의 기본값을 수정합니다. 시간 0은 F6을 누를 때까지 수동 수집합니다.

1. 터미널의 READY를 확인하고 F5로 기록을 시작합니다.
2. 시연 후 이동키를 놓고 SPACE로 정지한 다음 F6으로 수집을 끝냅니다.
3. FINISHING → UNSAVED를 기다리고, F7은 연습·실패, F9는 성공으로 저장합니다.
4. SAVED와 `LEKIWI_RECORD saved=...`를 확인합니다. 미저장 기록 폐기는 F10을 3초 안에 두 번 누릅니다.

**완료 기준:** 터미널에 나온 `data/recordings/lekiwi.*/episode.*`에 두 영상과 프레임 기록이 저장됩니다.
`.partial` 폴더는 미완료 기록입니다. 자세한 항목과 오류 처리는 [6편](isaacsim_basic/06_lekiwi_dataset/README.md)을 확인하세요.
새 F5 기록은 현재 자세에서 시작하며 로봇·큐브가 자동 초기화되지 않습니다. 같은 시작 배치는 아래 [배치 저장과 재현](#배치-저장과-재현)을 사용합니다.

기록 저장을 확인한 뒤 시뮬레이터를 정상 종료하고 8단계로 진행합니다.

## 8. 시연 선택·변환·학습 전 검사

```bash
./lekiwi dataset-ui
```

터미널에 표시된 `http://127.0.0.1:8765/#...` **전체 주소**를 같은 PC의 브라우저에서 엽니다.
이 화면은 Isaac Sim을 꺼도 사용할 수 있습니다. 계정이나 토큰을 입력할 필요는 없습니다.

1. 완료된 시연을 선택하고 첫 전방·손목 영상, 프레임 수, 성공 표시를 확인합니다.
2. 새 로컬 이름을 입력합니다. 아래 학습 예시를 그대로 따라가려면 **`basket_01`**을 사용합니다.
3. ‘선택한 시연 변환·검사’를 누릅니다. 여러 세션을 묶을 수 있지만 카메라 설정은 같아야 합니다.
4. 로컬 데이터셋 목록에서 `basket_01`을 선택하고 ‘상태·영상 검사’를 누릅니다.
5. 검사 완료와 프레임 수·저장 경로를 확인합니다.

**완료 기준:** `data/datasets/basket_01/recording_report.json`의 `complete`가 `true`이고 화면의 검사도 통과합니다.
원본은 그대로 보존됩니다. 같은 이름의 출력은 덮어쓰지 않으므로 재시도할 때는 새 이름을 사용하고 이후 학습 경로도 맞춰 바꿉니다.

같은 작업의 CLI는 아래와 같습니다. 화면으로 변환을 마쳤다면 이 변환 명령을 중복 실행할 필요는 없습니다.

```bash
./lekiwi dataset list
# SESSION/EPISODE는 위 목록의 실제 ID로 바꿉니다.
./lekiwi dataset export --episode lekiwi.SESSION/episode.EPISODE --name basket_01
./lekiwi dataset inspect --name basket_01
```

완료 후 관리 도구 터미널에서 Ctrl+C로 종료합니다. [로컬 데이터셋 관리 상세](docs/dataset-manager.md)

## 9. ACT 학습과 Isaac Sim 추론

브라우저 수업에서는 6장의 `06_train_act.py`, `07_infer_act.py`를 사용합니다.
학습은 1회 실행·모델 저장까지, 추론은 Isaac Sim에서 시작·정지·재시작까지 확인했습니다.
검증 데이터와 범위는 [ACT 실행 리허설 기록](docs/act-rehearsal-20260913.md)에 있습니다.
GPU·드라이버·CUDA 준비와 실제 과제 성공률 평가는 별도입니다.

현재 실습을 종료한 뒤 학습 설정 파일에서 데이터셋 이름, 새 `run_name`, 학습 횟수와 배치 크기를 수정합니다.
처음 실행 검사에는 `steps=1`, `batch_size=1`, `pretrained_backbone=False`를 사용합니다.
본 학습 기본값은 `pretrained_backbone=True`이며 최초 ResNet18 가중치 다운로드가 필요합니다.
아래는 **브라우저 편집기 터미널**에서 실행합니다. 앞에서 변환한 데이터셋의 실제 이름을 설정 파일에 입력합니다.

```bash
cd /workspace/isaacsim_basic/06_lekiwi_dataset/experiments
lesson stop
python3 06_train_act.py
lesson train status
lesson train logs
```

학습 결과는 `data/outputs/<run_name>/`에 저장됩니다. 기존 이름은 덮어쓰지 않습니다.
`train/checkpoints/last/pretrained_model`에 ACT와 정규화 통계,
`lekiwi_policy.json`에 상태·행동 순서, 단위와 카메라 설정을 함께 보관합니다.
브라우저의 **ACT 학습 결과**에서도 파일을 확인할 수 있습니다.
터미널 Ctrl+C는 대기만 끝냅니다. 서버 학습도 멈추려면 `lesson train stop`을 사용합니다.

추론은 `07_infer_act.py`의 `run_name`을 같은 값으로 저장하고 실행합니다.
`lesson status`가 READY이면 WebRTC 화면에 연결해 **R 시작 / Space 정지 / F8 장면 초기화**를 사용합니다.
`seconds`는 R을 누른 뒤 실행할 최대 시뮬레이션 시간입니다. 종료는 `lesson stop`입니다.

```bash
python3 07_infer_act.py
lesson status
lesson logs
```

학습과 같은 front/wrist RGB, 6개 절대 관절각(rad), base_link 속도(m/s·rad/s)를 사용합니다.
모델 계산 중에는 물리 시간을 멈추고 화면·정지 키를 처리합니다.
일시정지·장면 초기화·화면 연결 끊김·응답 오류 때는 추론을 해제하고, 다음 R에서 행동 큐를 초기화합니다.
이 기능은 Isaac Sim 가상 로봇 전용입니다. 실행 검사 모델의 동작 확인은 과제 성공률 평가와 구분합니다.

서버 터미널에서 직접 실행할 수도 있습니다.

```bash
./lekiwi act train --dataset-name basket_01 --run-name act_basket_01 --steps 1000 --batch-size 4
./lekiwi act infer --run-name act_basket_01 --seconds 30
```

공개 Hub 데이터는 `--dataset-name` 대신 `--repo-id 계정명/데이터셋명`을 사용합니다.
로컬 변환본은 기록의 카메라 설정을 사용하고, Hub 데이터는 이 프로젝트의 기본 카메라 설정을 전제로 합니다.
일반 LeRobot CLI를 직접 사용하려면 기존 `./lekiwi train act ...`도 유지됩니다.
수업 추론 연결에는 `06_train_act.py` 또는 `./lekiwi act train`이 저장하는 추가 규격 파일이 필요합니다.

## 10. 종료와 다음 실행

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

## 업데이트와 브랜치

현재 원격 수업 리허설은 통합 브랜치인 `develop`을 사용합니다. `test`는 별도 사전 점검용 브랜치로 유지합니다.
`main`은 리허설을 마친 수업 내용을 반영하는 안정 버전입니다. 본 수업 배포 브랜치는 강사가 별도 안내합니다.

나중에 업데이트할 때는 장비·시뮬레이터를 정상 종료하고 저장소에서 실행합니다.

```bash
git status --short
git branch --show-current
```

로컬 수정이 있다면 먼저 보존하고 충돌을 확인하세요. 강제 초기화로 해결하지 않습니다.
작업 트리가 깨끗하고 현재 브랜치가 `develop`인 경우 다음을 진행합니다.

```bash
git pull --ff-only origin develop
```

**데스크탑:** 라이선스에 동의한 터미널에서 `export ACCEPT_EULA=Y`와 필요한 `LEKIWI_DOCKER_SUDO=1`을 설정하고,
`./lekiwi setup all`과 `./lekiwi remote setup-editor`로 이미지를 갱신합니다.
**리더암 노트북:** 같은 브랜치의 코드를 갱신한 뒤 `./lekiwi remote setup-client`로 CPU 리더 이미지만 갱신합니다.
학생 Python 수정은 다음 실행에 반영됩니다. 공통 실행기·컨테이너 의존성 변경은 이미지 재빌드와 편집기 재시작이 필요합니다.
매 실행마다 빌드하지는 않습니다.
현재 프로젝트 이미지는 공개 레지스트리에 배포하지 않았으며 각 PC에서 빌드합니다.

## 참고 자료와 검증 범위

카메라 TF는 SOARM base 기준 측면 도면을 반영했습니다. 좌우 위치·광학 방향 등 최종 실물 확인은 남아 있습니다.
기존 에피소드의 카메라 설정과 개인 보정 파일은 자동 변경하지 않습니다.
개발 PC에서 리더 추종·연속 수집·데이터 변환·로컬 관리 화면을 확인했고,
손가락 충돌 형상 개선 후 실물 리더로 가상 큐브를 집는 조작에서 사용자가 개선을 확인했습니다.
900프레임 데이터의 ACT 학습 1회·모델 재로딩·시뮬레이션 추론을 확인했습니다.
새 PC의 드라이버 설치, 15쌍 동시 수업, 충분한 학습 뒤의 과제 성공률은 별도 검증 대상입니다.
[교육 실습 검증 기록](isaacsim_basic/VALIDATION.md)

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
├── recordings/   # 6편 원본 RGB·JSONL·manifest
├── datasets/     # 변환한 로컬 LeRobot 데이터셋
├── setup/        # 학생 PC 설치 상태·GPU 검사 결과
├── outputs/      # 학습 출력
└── cache/, logs/, isaac-data/, home/  # 캐시·설정
~~~

다음 검사는 GUI/teleop을 모두 종료한 후 하나씩 실행하세요.
리더 USB를 사용하지 않으며 실제 집기 성공 검사를 대신하지 않습니다.

~~~bash
./lekiwi validate-usd
./lekiwi test-physics
./lekiwi test-arm
./lekiwi test-gripper
./lekiwi test-scene
./lekiwi test-cameras
./lekiwi test-basic
./lekiwi test-recording
~~~

`test-basic`은 기초 물리·관절 장면을, `test-recording`은 한 관절의 180프레임 기록·저장·재생을 검사합니다.

일반 사용자는 build-assets를 실행할 필요가 없습니다.
원본 CAD/ROS 작업 폴더 src/와 isaac_sim_bundle/은 배포에 필요하지 않아 저장소에 포함하지 않습니다.

## 폴더 구조

~~~text
lekiwi                 # 학생과 개발자가 사용하는 실행 명령
compose.yaml           # Docker 서비스와 공통 데이터 연결
docker/                # 이미지 빌드·컨테이너 진입점
isaac_sim/             # 로봇 실행·카메라·코스·GPU 검사
  assets/              # 배포용 URDF·USD·mesh·기본 카메라 TF
isaacsim_basic/         # 0장 환경 설정·1~6편 교재·이미지·ZIP·교육 전용 코드
tools/
  host_setup/          # 호스트 설치·환경 검사
  dataset_manager/     # 로컬 시연 선택·변환·검사 화면과 CLI
  *.py                 # LeRobot 검사·리더 입력·데이터 변환
tests/                 # 하드웨어 없이 실행하는 공통 자동 테스트
docs/                  # 설치·구조·기능 설명
data/                  # 개인 보정·기록·데이터셋·설치 진단 (Git 제외)
~~~

로컬 CAD/ROS 참조 폴더 `src/`, `isaac_sim_bundle/`, `.local_ros/`는 Git과 Docker 빌드에서 제외되어 학생의 clone에는 포함되지 않습니다.
기존 원본·개인 데이터는 폴더 정리 과정에서 이동하거나 삭제하지 않습니다. [도구별 역할](tools/README.md)을 참고하세요.

## 상세 문서

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
