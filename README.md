# LeKiwi Isaac Sim · 설치부터 로컬 데이터 수집까지

학생은 **`develop` 브랜치를 받은 뒤 이 문서의 번호 순서대로 진행**합니다.
교육 흐름은 **환경 설정 → 기초 교육 → teleop → 로컬 데이터 수집·변환 → 로컬 학습 → 추론**입니다.
데이터셋 계정 연결이나 업로드 단계는 없습니다.

실제 SO101 리더암과 키보드로 **Isaac Sim 안의 LeKiwi 베이스와 SOARM**을 조작합니다.
실제 follower나 실제 LeKiwi 본체를 움직이는 기능은 없습니다.
로봇 URDF·USD·mesh와 교재는 저장소에 포함되며, Isaac Sim·LeRobot은 Docker 안에서 실행합니다.

| 단계 | 이번 저장소에서 진행할 범위 |
|---|---|
| 1~3 · PC 준비 | 설치 도구와 개발 PC 실행 검사 준비. 새 PC의 드라이버 신규 설치·재부팅은 현장 검증 필요 |
| 4~8 · 교육·teleop·데이터 | 교재 1~6편, 리더 추종, 두 카메라 기록, 로컬 변환·검사 구현 |
| 9 · ACT 학습 | CLI 연결과 실행 예시 제공. 우리 데이터로 학습 완료·모델 재로딩 검증은 아직 남음 |
| 추론 | 학습한 모델의 Isaac Sim 제어 연결은 아직 없음. 후속 개발 단계 |

지원 설치 환경은 **Ubuntu 22.04/24.04 x86_64, 로컬 데스크톱, NVIDIA GPU**입니다.
Windows·WSL·macOS·ARM은 자동 설치 대상이 아닙니다.
RAM·VRAM이 공식 최소보다 적어도 경고 후 설치를 시도하지만 모든 GPU에서 실행을 보장하지 않습니다.
상세 조건은 [학생 PC 설치 안내](docs/student-setup.md)를 확인하세요.

<a id="2-저장소-받기"></a>

## 1. 새 PC에서 develop 받기

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

1. 사용 가능한 NVIDIA 드라이버가 있으면 유지합니다. 없거나 오래되었으면 GPU가 지원하는 580 계열 후보를 확인합니다.
2. 드라이버 설치로 재부팅이 필요하면 중단하고 안내합니다. 직접 작업을 저장하고 재부팅합니다. Secure Boot의 MOK 등록이 필요하면 화면 안내를 완료합니다.
3. Docker Engine·Compose·NVIDIA Container Toolkit을 준비합니다.
4. Isaac Sim·LeRobot 이미지를 빌드하고 CUDA·두 카메라·짧은 기록을 검사합니다.

재부팅한 경우 저장소 폴더로 돌아와 `export ACCEPT_EULA=Y`와 `./lekiwi install`을 다시 실행합니다.
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

## 4. 기초 교육 1~6편 진행

아래 교재를 순서대로 읽고 각 편의 캡처·실습 기록지를 작성합니다.
장면을 바꿀 때는 기존 Isaac Sim을 정상 종료한 뒤 다음 명령을 실행합니다.

| 편 | 교재 | 시작 명령·이 문서의 연결 단계 |
|---|---|---|
| 1 | [객체와 물리 성질](isaacsim_basic/01_object_physics/README.md) | `./lekiwi basic` · Collider, 질량·중력, 마찰·반발력 |
| 2 | [로봇과 관절](isaacsim_basic/02_robot_joints/README.md) | `./lekiwi basic --lesson joints` · 회전축·제한·Drive |
| 3 | [전방·손목 카메라](isaacsim_basic/03_robot_cameras/README.md) | `./lekiwi sim` · 시점·가림·좌표 |
| 4 | [원격 조작](isaacsim_basic/04_teleoperation/README.md) | 키보드는 `./lekiwi scene`, 리더는 아래 5~6단계 |
| 5 | [기초 데이터 기록](isaacsim_basic/05_data_recording/README.md) | `./lekiwi basic --lesson recording` · 한 관절 JSON 기록·재생 |
| 6 | [LeKiwi 데이터셋 수집](isaacsim_basic/06_lekiwi_dataset/README.md) | 아래 7~8단계 · 두 영상·상태·행동 수집과 로컬 변환 |

각 편은 MD·실습 기록지·실제 화면·노션용 ZIP을 포함합니다. [교재 전체 목차](isaacsim_basic/README.md)
1·2편은 Stage/Property를 사용하며, 3~6편의 해당 실습 창은 Stage 옆 탭에 배치됩니다.
교육 편성은 설치 완료 PC 기준 **2일, 총 12~14시간**의 계획용 추정입니다.
최초 설치·충분한 집기 시연 확보·실측 카메라 보정·학습은 별도입니다.

리더가 없으면 5~6단계 장비 실습을 건너뛰고 7단계의 키보드 기록을 진행할 수 있습니다.
5편의 한 관절 JSON은 기록 개념을 배우는 예제이며, 본격적인 로봇 데이터는 6편에서 수집합니다.

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
이어서 `Lesson 6 - LeKiwi Recording` 탭에서 진행합니다.

1. Task를 선택합니다. 첫 저장 검사는 직진·정지, 팔 시연은 블록 운반 과제를 사용합니다.
2. Max seconds를 설정합니다. 첫 검사는 1~3초로 시작하고, 실제 수집에서는 원하는 초를 입력합니다. **0은 수동 종료**이며 시뮬레이션 시간 기준입니다.
3. Record를 누르고 시연합니다. 기록 중에는 타임라인의 Pause/Stop을 누르지 않습니다.
4. 이동키를 놓고 Stop recording을 누르거나 시간 제한이 끝나기를 기다립니다. 리더 조작 중에는 Space로 가상 베이스 정지·팔 목표 유지를 요청할 수 있습니다.
5. FINISHING이 끝나 UNSAVED가 되면 결과를 검토합니다. 성공한 경우에만 성공 표시를 선택하고 Save episode를 누릅니다.
6. **SAVING → SAVED**를 확인합니다. 잘못된 미저장 기록은 Discard unsaved로 버립니다.

**완료 기준:** 패널에 표시된 `data/recordings/lekiwi.*/episode.*`에 두 영상과 프레임 기록이 저장됩니다.
`.partial` 폴더는 미완료 기록입니다. 자세한 항목과 오류 처리는 [6편](isaacsim_basic/06_lekiwi_dataset/README.md)을 확인하세요.
새 Record는 현재 자세에서 시작하며 로봇·큐브가 자동 초기화되지 않습니다. 같은 시작 배치는 아래 [배치 저장과 재현](#배치-저장과-재현)을 사용합니다.

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

## 9. 로컬 ACT 학습 — 강사와 함께 검증할 단계

**여기부터는 우리 데이터로 학습 완료·모델 재로딩을 아직 검증하지 않은 단계입니다.**
1~8단계가 끝나면 새 PC의 설치·teleop·수집·변환 검증은 완료한 것입니다.
아래는 학습 실행을 확인하기 위한 예시이며, 집기 성공을 보장하는 완성 학습 설정이 아닙니다.
Isaac Sim과 데이터셋 관리 화면을 종료해 GPU 메모리를 확보한 뒤 강사와 함께 진행합니다.

```bash
./lekiwi check-ml
./lekiwi dataset inspect --name basket_01
./lekiwi train act \
  --dataset.repo_id=local/basket_01 \
  --dataset.root=/data/datasets/basket_01 \
  --output_dir=/data/outputs/act_basket_01_check \
  --batch_size=4 --steps=100
```

`local/basket_01`은 8단계 도구가 만드는 내부 식별자이며 온라인 저장소를 뜻하지 않습니다.
다른 이름으로 변환했다면 이름과 경로를 함께 바꾸세요. 기존 데이터는 `recording_report.json`의 `repo_id`를 사용합니다.
학습 출력 폴더가 이미 있으면 지우거나 덮어쓰지 말고 새 출력 이름으로 실행합니다.
선택한 모델의 사전학습 가중치는 최초 다운로드가 필요할 수 있습니다. 데이터셋은 로컬에서 읽습니다.

**검증할 항목:** 데이터와 두 영상 읽기, 유한한 학습 손실, 설정한 학습 횟수 완료,
`data/outputs/act_basket_01_check/checkpoints` 아래 모델 저장 여부입니다.
GPU 메모리가 부족하면 학습 프로세스의 오류를 확인하고 배치 크기를 줄여 새 출력 폴더로 다시 검사합니다.
짧은 실행 성공 이후에 학습용 시연의 품질·수량을 검토하고 본 학습과 모델 재로딩을 검증합니다.

학습 상태·재개를 관리하는 화면과 **학습 모델로 Isaac Sim을 조작하는 추론 기능은 아직 없습니다.**
GR00T는 의존성과 CLI만 준비되어 있으며 이 순서도의 첫 학습 대상으로 사용하지 않습니다.

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

학생은 `develop`을 사용합니다. `main`은 현재 초기 teleop 버전이며 최신 교육·설치 기능의 기준이 아닙니다.
`feature/isaacsim_basic`은 작업 브랜치이고 PR로 `develop`에 통합합니다.

나중에 업데이트할 때는 장비·시뮬레이터를 정상 종료하고 저장소에서 실행합니다.

```bash
git status --short
git pull --ff-only origin develop
./lekiwi setup all
```

로컬 수정이 있다면 먼저 보존하고 충돌을 확인하세요. 강제 초기화로 해결하지 않습니다.
코드·교재는 이미지에 복사되므로 업데이트 후 재빌드해야 반영됩니다. 매 실행마다 빌드하지는 않습니다.
현재 프로젝트 이미지는 공개 레지스트리에 배포하지 않았으며 각 PC에서 빌드합니다.

## 참고 자료와 검증 범위

카메라 TF는 SOARM base 기준 측면 도면을 반영했습니다. 좌우 위치·광학 방향 등 최종 실물 확인은 남아 있습니다.
기존 에피소드의 카메라 설정과 개인 보정 파일은 자동 변경하지 않습니다.
개발 PC에서 리더 추종·연속 수집·데이터 변환·로컬 관리 화면을 확인했으며, 새 PC의 신규 드라이버 설치와
학습·모델 재로딩·추론은 별도 검증 대상입니다. [교육 실습 검증 기록](isaacsim_basic/VALIDATION.md)

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
isaacsim_basic/         # 1~6편 교재·이미지·ZIP·교육 전용 코드
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
