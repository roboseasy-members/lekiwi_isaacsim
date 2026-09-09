# Isaac Sim Basic · 1~6편

Isaac Sim **5.1.0**, Ubuntu 데스크톱, Docker 기준 교육자료입니다.
객체 물리 → 관절 → 카메라 → 조작 → 데이터 기록 순서로 진행합니다.
각 편은 **교재 MD · 실습 기록지 · 실제 화면과 빨간 표시 · 출처 · 노션용 ZIP**을 포함합니다.
1~3편·5편·6편 키보드 기록과 4편 앞부분은 실물 장비 없이 가능합니다. 4편의 리더 실습에는 실제 SO101 리더와 LeRobot 이미지가 필요합니다.

## 편별 교재와 노션 ZIP

| 편 | 교재 | 내용 | 노션용 ZIP | 실제 화면 |
|---|---|---|---|---:|
| 1 | [객체 생성과 물리 속성](01_object_physics/README.md) | Collider, Rigid Body, 질량·중력·마찰·반발력, 열린 바구니 | [다운로드](01_object_physics/01_object_physics_notion.zip) | 12장 + 개념도 |
| 2 | [로봇 구조와 관절](02_robot_joints/README.md) | 링크, 회전 중심·축·제한, Drive 목표·구동값, SO101 대응 | [다운로드](02_robot_joints/02_robot_joints_notion.zip) | 6장 |
| 3 | [전방·손목 카메라와 좌표](03_robot_cameras/README.md) | 시점·화각·클리핑, 렌즈 중심, TF 환산, 가림 진단 | [다운로드](03_robot_cameras/03_robot_cameras_notion.zip) | 7장 |
| 4 | [키보드·리더암 조작](04_teleoperation/README.md) | 주행·정지·속도, 리더 준비·보정·활성화, 로그와 집기 과제 | [다운로드](04_teleoperation/04_teleoperation_notion.zip) | 4장 |
| 5 | [데이터 수집과 저장·재생](05_data_recording/README.md) | 관측·행동·시간 대응, 에피소드 저장·재생·검사 | [다운로드](05_data_recording/05_data_recording_notion.zip) | 7장 |
| 6 | [LeKiwi 영상·명령과 데이터셋](06_lekiwi_dataset/README.md) | 두 RGB·상태·행동 수집, 성공 표시, LeRobot 변환·검사 | [다운로드](06_lekiwi_dataset/06_lekiwi_dataset_notion.zip) | 6장 + 변환 터미널 1장 |

5편은 한 관절 JSON으로 개념을 익히고, 6편은 LeKiwi의 두 RGB·관측·행동을 기록해 로컬 LeRobot 데이터셋으로 변환합니다. 학습·정책 실행은 후속 범위입니다.
이후 과정은 **로컬 데이터셋 검수 → ACT 학습 → Isaac Sim 추론·평가**로 이어집니다. 외부 계정 연결과 데이터셋 업로드 단계는 포함하지 않습니다.
[로컬 데이터셋 관리 화면](../docs/dataset-manager.md)에서 시연 선택·변환·검사를 진행할 수 있습니다.
4편 실물 리더 절차는 구현과 기존 안내를 바탕으로 작성했으며, 이번 교재 제작에서 실물 연결·보정을 새로 수행하지 않았습니다.

6편의 키보드 기록은 실물 없이 가능하며, 데이터셋 변환에는 LeRobot 이미지가 필요합니다.


## 1~6편의 기본 화면과 초기화

| 편 | 기본 화면 | 반복 실습 방법 |
|---|---|---|
| 1·2 | Perspective 하나 | Stage 옆 실습 탭의 **Reset simulation (keep edits)**. Play 이전 상태로 돌아가며 객체·물리 속성·Drive 설정 유지 |
| 3·4 | 좌측 Perspective / 우측 Front Camera | 조작 탭의 **Reset scene / randomize cubes**. 로봇 시작 자세 + 색상 라인별 새 큐브 위치·방향 |
| 5 | Perspective 하나 + 기록 탭 | **Reset model (keep saved episodes)**. 모형 초기화, 저장 기록 보존, 미저장·진행 중에는 차단 |
| 6 | 좌측 Perspective / 우측 Front Camera + FRONT·WRIST 기록 미리보기 | 저장·폐기 완료 후 조작 탭에서 랜덤 리셋. 다음 기록에 새 배치 정보 저장 |

LeKiwi의 `C`·`T`는 좌측 화면을 변경합니다. 우측 전방 카메라는 유지됩니다.
리셋은 실제 리더암을 움직이지 않습니다. teleop에서는 리셋 후 `R`로 다시 활성화합니다.
최신 실행 파일을 받았다면 `./lekiwi setup sim`으로 이미지를 갱신한 뒤 실습하세요.

## 1~6편의 카메라 설정 적용 범위

LeKiwi의 전방·손목 카메라는 이미지 안의 `/opt/lekiwi/isaac_sim/assets/cameras/mounts.json`을 공통으로 사용합니다.
SOARM base 기준 측면 도면의 렌즈 중심은 front `(86.91, 0, -59.28)` mm,
wrist `(205.40, 0, 208.58)` mm입니다. 손목 값은 도면 재현 자세에서 손목 링크 기준으로 환산했습니다.
Y=0·손목 전방 아래 45°는 현재 채택한 해석이며, 최종 실물 확인 전까지 `calibrated=false`입니다.

| 편 | 적용 범위 |
|---|---|
| 1 · 물리 | 기본 도형 실습에는 LeKiwi 장착 카메라가 없습니다. 직접 만든 Camera는 별도 실습 객체입니다. |
| 2 · 관절 | 단일 관절 실습에는 장착 카메라가 없습니다. LeKiwi 실행으로 넘어가면 공통 설정을 사용합니다. |
| 3 · 카메라 | `sim`의 전방·손목 시점과 optical frame에 적용합니다. |
| 4 · 조작 | `sim`·`scene`·`teleop`에서 같은 설정으로 팔을 따라갑니다. |
| 5 · 기초 기록 | 단일 관절 JSON 실습입니다. LeKiwi RGB 수집은 6편에서 진행합니다. |
| 6 · 데이터셋 | `record`·`teleop --record`의 두 RGB와 새 에피소드의 `camera_config`에 적용합니다. |

수정 전 이미지를 사용 중이면 창을 정상 종료하고 `./lekiwi setup sim`으로 다시 빌드한 뒤 해당 편을 실행합니다.
`LEKIWI_CAMERA_CONFIG`로 개인 복사본을 지정했다면 그 파일이 기본값보다 우선합니다.
최신 기본값으로 실습하려면 별도 설정을 해제하거나 `LEKIWI_CAMERA_CONFIG= ./lekiwi record`처럼 빈 값을 명시합니다.
기존 개인 설정·저장된 장면·에피소드의 카메라 값은 자동으로 덮어쓰지 않습니다.
자세한 좌표·환산식은 [3편](03_robot_cameras/README.md)과 [카메라 설정 문서](../docs/robot-cameras.md)를 참고하세요.

## 교육 시간과 운영안

**처음 배우는 교육생이 직접 조작하고 기록지까지 작성한다면 2일, 하루 6~7시간으로 편성하는 것을 권합니다.**
아래 시간은 교재의 비교 실험·과제 수를 바탕으로 잡은 **계획용 추정치**이며 실제 수강생 수업을 재서 얻은 값은 아닙니다.
PC별 이미지 빌드와 첫 실행을 마쳤고, 기본 터미널 조작이 가능하며, 리더 실습은 강사의 도움을 받을 수 있다고 가정합니다.

| 편 | 기본 교육 시간 | 포함하는 활동 | 선택 실습 추가 |
|---|---:|---|---:|
| 1 · 객체와 물리 | 90~150분 | 기본 60~90분 + 바구니·오류 진단·심화·저장 30~60분 | — |
| 2 · 로봇과 관절 | 60~90분 | 축·앵커·Drive·한계 비교와 과제 | — |
| 3 · 카메라와 좌표 | 60~90분 | 시점·화각·가림·좌표 해석과 기록 | 실측 TF 보정은 별도 |
| 4 · 조작 | 30~45분 | 키보드 주행·정지·속도 비교 | 리더 준비·보정·방향·집기 60~90분 |
| 5 · 기초 기록 | 45~60분 | 한 관절 에피소드 저장·재생·JSON 해석 | — |
| 6 · LeKiwi 데이터셋 | 90~120분 | 짧은 키보드 기록 2개, 시간 설정, 파일 해석·변환·검사 | 준비된 리더로 수집 30~60분 |

- **실물 없이 1~6편:** 순수 교육 375~555분, 즉 **6시간 15분~9시간 15분**입니다.
- **4·6편 리더 실습까지:** 순수 교육 465~705분, 즉 **7시간 45분~11시간 45분**입니다.
- 쉬는 시간·질문·결과 정리를 포함한 전체 편성은 **12~14시간을 2일에 나누는 안**으로 잡습니다. 점심은 별도입니다.
- 권장 배치: **1일차 1~3편**, **2일차 4~6편**. 하루만 가능하면 4편 리더와 1편 심화 일부를 다음 시간으로 분리합니다.

최초 드라이버·Docker·이미지 준비는 수업 전 별도로 진행하세요. 준비가 안 된 PC는 계획상 **1~3시간 이상**의 추가 여유를 두되,
다운로드 속도·드라이버 문제에 따라 더 걸릴 수 있습니다. 강사는 수업 전에 모든 PC에서 `./lekiwi doctor`, 이미지 빌드와 첫 GUI 실행을 확인합니다.
리더를 여러 명이 공유한다면 위 실습 시간 외에 장비 대기·교대 시간이 필요합니다.

6편의 초 단위 제한은 벽시계 시간이 아니라 **시뮬레이션 시간**입니다. 처음에는 1~3초 제한이나 짧은 수동 종료로
저장·변환 경로를 확인하세요. 120초·300초는 설정 예시이며 수업에서 그 길이를 모두 채울 필요는 없습니다.
실측 카메라 TF 보정, 충분한 집기 시연 확보, 모델 학습·평가는 위 교육 시간에 포함하지 않습니다.

## 처음 시작하기

학생 PC에서는 저장소를 받은 뒤 `./lekiwi install --check`와 `./lekiwi install`로 준비할 수 있습니다.
공식 RAM·VRAM 최소 사양 미달도 안내 후 설치를 허용하며, 준비 후 실제 CUDA·카메라·60프레임 기록 검사를 수행합니다.
드라이버 변경과 재부팅 절차는 [학생 PC 설치 안내](../docs/student-setup.md)를 참고하세요.


1. [저장소의 순서별 설치 안내](../README.md#1-새-pc에서-develop-받기)를 따라 NVIDIA 드라이버,
   Docker Compose, NVIDIA Container Toolkit, X11/XWayland 및 xauth를 준비합니다.
2. clone한 저장소의 최상위 폴더에서 아래 명령을 실행합니다.
   Docker에 sudo가 필요한 PC에서만 첫 번째 export를 사용합니다.
   `ACCEPT_EULA=Y`는 [NVIDIA 라이선스](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-software-license-agreement/)
   를 읽고 동의한 경우에 설정합니다.

```bash
export LEKIWI_DOCKER_SUDO=1
export ACCEPT_EULA=Y
./lekiwi doctor
./lekiwi setup sim
./lekiwi basic
```

이미지 빌드에는 인터넷이 필요합니다. 기초 실습은 이미지에 포함된 코드로 기본 도형을 생성하므로
로봇 모델이나 외부 USD를 추가 다운로드하지 않습니다. 1~3편·5편과 4편 키보드 실습에는 LeRobot 이미지가 필요하지 않습니다. 4편 리더 실습 또는 6편 변환을 시작할 때 `./lekiwi setup all`로 준비합니다.
새 터미널에서는 위 환경변수를 다시 설정하거나 저장소의 `.env.example`을 참고하세요.

3. [첫 교육자료: 객체 생성과 물리 속성](01_object_physics/README.md)을 따라갑니다.
   비교 결과와 과제는 [실습 기록지](01_object_physics/worksheet.md)에 작성합니다.

전체 6편에는 **실제 실습 화면 39장과 빨간 테두리 안내**가 포함되어 있습니다.
VS Code에서 Markdown을 열고 `Ctrl + Shift + V`로 미리보기를 켜면 그림과 표를 함께 볼 수 있습니다.

## 폴더와 Docker의 관계

| 용도 | Git 저장소 / 호스트 | 컨테이너 내부 |
|---|---|---|
| 교재·그림·실습 코드 | `isaacsim_basic/` | `/opt/lekiwi/isaacsim_basic/` |
| 교육생이 편집하는 장면 | `data/isaacsim_basic/<실습명>.<고유값>/scene.usda` | `/data/isaacsim_basic/<실습명>.<고유값>/scene.usda` |
| 교육생 캡처·과제 결과 | `data/isaacsim_basic/` 안에 저장 | `/data/isaacsim_basic/` 안에 저장 |

교재는 Dockerfile의 `COPY`로 이미지에 들어갑니다. 컨테이너 안에만 원본을 작성하지 않습니다.
따라서 저장소를 받은 다른 PC에서도 같은 이미지 빌드 과정을 사용할 수 있습니다.
**수정한 교재·코드를 반영하려면 `./lekiwi setup sim`을 다시 실행합니다.**
이 교육자료는 `develop`에 통합되어 있습니다. 저장소의 clone 안내에서 `develop`을 선택하세요.

실습 결과는 기존 `/data` bind mount를 사용해 컨테이너 종료 후에도 남습니다.
`LEKIWI_DATA_DIR`를 변경했다면 호스트의 `data/` 대신 지정한 폴더에서 찾으세요.
결과·로그는 Git에서 제외되며, 실습 원본과 교재는 Git 관리 대상입니다.
5편의 에피소드 JSON은 `data/isaacsim_basic/recording.*/episode.*/`에 저장합니다.
6편 원본은 `data/recordings/`, 변환한 LeRobot 데이터셋은 `data/datasets/`에 저장합니다.

## 실습 창의 위치

1·2편은 오른쪽의 기본 **Stage / Property** 창에서 실습합니다.
3·4편의 `LeKiwi + SO101 Physical Drive`, 5편의 `Lesson 5 - Data Recording`,
6편의 `Lesson 6 - LeKiwi Recording`은
실행 시 **Stage와 같은 영역에 탭으로 자동 배치**되고 조작 안내가 먼저 표시됩니다.
객체를 찾거나 속성을 수정할 때는 **Stage** 탭을 누르고, 조작하려면 해당 실습 탭으로 돌아갑니다.
탭 제목을 드래그하면 필요에 따라 별도 창으로 분리할 수도 있습니다.

## 실습 장면 선택

한 장면을 마치면 Isaac Sim 창을 닫고 종료를 기다린 다음 다음 명령을 실행합니다.
아래 `basic` 장면은 **정지 상태**에서 시작합니다. Play는 교육생이 누릅니다.
3·4편의 `sim`/`teleop`과 6편의 `record`는 물리 계산이 자동 시작되므로 각 편의 안내를 따릅니다.
5편 `recording`은 패널의 Record로 관절 운동을 시작합니다.

| 명령 | 시작 상태와 목적 |
|---|---|
| `./lekiwi basic` | 바닥·조명·중력이 있는 실습대. 큐브를 직접 생성 |
| `./lekiwi basic --lesson drop` | 세 큐브의 물리 설정 차이 확인 |
| `./lekiwi basic --lesson mass` | 0.1 kg / 1 kg 큐브의 낙하 비교·중력 변경 |
| `./lekiwi basic --lesson friction` | 15° 경사로 두 개에서 마찰 비교 |
| `./lekiwi basic --lesson bounce` | 반발력 0 / 0.8인 공과 받침 비교 |
| `./lekiwi basic --lesson basket` | 바닥·네 벽으로 만든 열린 바구니에 큐브 낙하 |
| `./lekiwi record` | LeKiwi 키보드 주행과 두 카메라 수집 패널 |
| `./lekiwi basic --lesson recording` | 한 관절의 기록·저장·재생 패널. Record로 시작 |
| `./lekiwi basic --lesson joints` | 고정 받침 + 한 회전 관절: 목표·제한·구동 비교 |

새 실행은 항상 새 작업 파일을 만듭니다. 이전 파일은 `File > Open`으로 직접 엽니다.
파일 경로는 시작 터미널의 `ISAACSIM_BASIC ready` 줄에 출력됩니다.
기존 teleop/scene과 같은 시뮬레이터 중복 실행 방지를 사용합니다.

## 1편의 세부 학습 순서

- 기본 실습: 화면·좌표 → 객체 생성 → Rigid Body/Collider → 질량·중력 → 마찰·반발력.
- 응용 실습: 바구니 충돌 모양 → 잘못된 설정 진단 → 저장·재열기 → 최종 과제.
- 심화 읽기: 무게중심·관성, CCD, 접촉 여유 거리, 물리 계산 간격.

수업 시간 제안은 기본 60~90분, 응용·심화 30~60분입니다. 실제 소요 시간은 PC와 수강생 경험에 따라 달라집니다.

## 검증

Isaac Sim 창을 닫은 상태에서 실행합니다.

```bash
./lekiwi test-basic
./lekiwi test-recording  # 5편의 기록·저장·재생 검사
```

Docker 내부의 실제 PhysX로 낙하, 질량 비교, 경사로 마찰, 반발력 차이,
바구니 안착과 교육용 관절의 양방향 추종·60° 제한을 확인합니다. 성공 시 마지막에 `ISAACSIM_BASIC_TEST result=PASS`가 출력됩니다.
이 명령은 결과 확인용이며 GUI 버튼 실습을 대신하지 않습니다.

각 편의 `SOURCES.md`에 출처와 실제 검증 범위를 기록합니다. 전체 결과는 [검증 기록](VALIDATION.md)을 참고하세요.


## 파일 구조와 보는 방법

```text
isaacsim_basic/
  README.md                       전체 목차
  01_object_physics/               2~6편도 동일 구조
    README.md                     교재
    worksheet.md                  실습 기록지
    SOURCES.md                    출처·검증 범위
    images/
      screenshots/                실제 화면 원본 PNG
      annotations.json            빨간 사각형 위치·설명
      *.svg                       원본을 포함한 벡터 표시
      *.png                       교재·노션용 이미지
    01_object_physics_notion.zip   HTML + 이미지 패키지
  scenes.py / run.py              1·2편 실습 장면 생성·실행
  smoke_test.py                   Docker 물리 검사
  export_lessons.py               강사용 패키지 재생성 도구
```

VS Code에서 각 편 `README.md`를 열고 **Ctrl+Shift+V**를 누릅니다.
교재를 다른 곳으로 옮길 때는 **해당 편 폴더 전체**를 함께 옮겨야 이미지가 유지됩니다.
실습 기록지는 `data/isaacsim_basic/` 같은 개인 결과 폴더로 복사해서 작성하세요.

## 노션으로 가져오기

1. 원하는 편의 `*_notion.zip`을 준비합니다. ZIP을 다시 압축할 필요는 없습니다.
2. 노션에서 **설정 → 가져오기(Import) → Convert Zip to pages**를 선택하거나 페이지에서 `/zip`을 입력합니다.
3. ZIP을 선택하고 가져온 교재·기록지·출처 페이지의 이미지와 표를 확인합니다.
4. 원본 MD는 별도로 보관합니다. 단독 MD를 복사·붙여넣으면 로컬 이미지가 자동 업로드되지 않을 수 있습니다.

ZIP에는 `README.html`, `worksheet.html`, `SOURCES.html`과 교재가 사용하는 PNG만 포함합니다.
HTML과 MD를 동시에 넣어 같은 교재가 두 번 생기는 것을 피했습니다.
다른 편·저장소 파일로 가는 링크는 편별 ZIP 안에 없는 파일을 가리키므로 전체 교재 MD에서 열도록 안내합니다.

[노션 공식 가져오기 안내](https://www.notion.com/help/import-data-into-notion)를 기준으로 구성했습니다.
**실제 노션 계정에 업로드하여 가져오는 검증은 수행하지 않았습니다.**
ZIP 무결성, 포함 이미지, HTML 내부 링크는 로컬에서 검사합니다.

## 강사가 내용을 수정한 뒤

교육생은 이미 만들어진 PNG·ZIP을 사용하면 됩니다. 재생성 도구는 호스트 Ubuntu의
`python3-markdown-it`, `python3-gi`, `python3-cairo`, `gir1.2-rsvg-2.0`을 사용합니다.
이 패키지는 교재 재생성용이며 Isaac Sim 실행 의존성은 아닙니다.

```bash
# 원본 캡처와 annotations.json을 수정했다면 해당 편의 강조 SVG 재생성
python isaacsim_basic/01_object_physics/images/build_annotations.py isaacsim_basic/02_robot_joints/images
# 전체 편의 PNG와 노션 ZIP 재생성
/usr/bin/python3 isaacsim_basic/export_lessons.py
# 수정한 교재·이미지를 Docker에 반영
./lekiwi setup sim
```

원본 캡처는 Isaac Sim 창만 찍고, 커서·툴팁·선택 표시가 필요한 내용을 가리지 않는지 확인합니다.
노션 업로드용 ZIP에는 비밀번호·로그·개인 보정 파일·ROS/RViz 파일이 들어가지 않습니다.
