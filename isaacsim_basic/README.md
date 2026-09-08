# Isaac Sim Basic · 1~4편

Isaac Sim **5.1.0**, Ubuntu 데스크톱, Docker 기준 교육자료입니다.
객체 물리 → 관절 → 카메라 → 조작 순서로 진행합니다.
각 편은 **교재 MD · 실습 기록지 · 실제 화면과 빨간 표시 · 출처 · 노션용 ZIP**을 포함합니다.
1~3편과 4편 앞부분은 실물 장비 없이 가능합니다. 4편의 리더 실습에는 실제 SO101 리더와 LeRobot 이미지가 필요합니다.

## 편별 교재와 노션 ZIP

| 편 | 교재 | 내용 | 노션용 ZIP | 실제 화면 |
|---|---|---|---|---:|
| 1 | [객체 생성과 물리 속성](01_object_physics/README.md) | Collider, Rigid Body, 질량·중력·마찰·반발력, 열린 바구니 | [다운로드](01_object_physics/01_object_physics_notion.zip) | 11장 + 개념도 |
| 2 | [로봇 구조와 관절](02_robot_joints/README.md) | 링크, 회전 중심·축·제한, Drive 목표·구동값, SO101 대응 | [다운로드](02_robot_joints/02_robot_joints_notion.zip) | 5장 |
| 3 | [전방·손목 카메라와 좌표](03_robot_cameras/README.md) | 시점·화각·클리핑, 렌즈 중심, TF 환산, 가림 진단 | [다운로드](03_robot_cameras/03_robot_cameras_notion.zip) | 7장 |
| 4 | [키보드·리더암 조작](04_teleoperation/README.md) | 주행·정지·속도, 리더 준비·보정·활성화, 로그와 집기 과제 | [다운로드](04_teleoperation/04_teleoperation_notion.zip) | 4장 |

5·6편의 데이터 수집·학습은 이번 범위에 포함하지 않습니다.
4편 실물 리더 절차는 구현과 기존 안내를 바탕으로 작성했으며, 이번 교재 제작에서 실물 연결·보정을 새로 수행하지 않았습니다.

## 처음 시작하기

1. [저장소의 PC 준비·clone 안내](../README.md#1-처음-한-번-pc-준비)를 따라 NVIDIA 드라이버,
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
로봇 모델이나 외부 USD를 추가 다운로드하지 않습니다. 1~3편에는 LeRobot 이미지가 필요하지 않습니다. 4편 리더 실습을 시작할 때 `./lekiwi setup all`로 준비합니다.
새 터미널에서는 위 환경변수를 다시 설정하거나 저장소의 `.env.example`을 참고하세요.

3. [첫 교육자료: 객체 생성과 물리 속성](01_object_physics/README.md)을 따라갑니다.
   비교 결과와 과제는 [실습 기록지](01_object_physics/worksheet.md)에 작성합니다.

전체 4편에는 **실제 Isaac Sim 화면 27장과 빨간 테두리 안내**가 포함되어 있습니다.
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
이 교육자료는 `feature/isaacsim_basic` 브랜치에 포함되어 있습니다. 저장소의 clone 안내에서 해당 브랜치를 선택하세요.

실습 결과는 기존 `/data` bind mount를 사용해 컨테이너 종료 후에도 남습니다.
`LEKIWI_DATA_DIR`를 변경했다면 호스트의 `data/` 대신 지정한 폴더에서 찾으세요.
결과·로그는 Git에서 제외되며, 실습 원본과 교재는 Git 관리 대상입니다.

## 실습 장면 선택

한 장면을 마치면 Isaac Sim 창을 닫고 종료를 기다린 다음 다음 명령을 실행합니다.
아래 `basic` 장면은 **정지 상태**에서 시작합니다. Play는 교육생이 누릅니다.
3·4편의 `sim`/`teleop`은 물리 계산이 자동 시작되므로 각 편의 안내를 따릅니다.

| 명령 | 시작 상태와 목적 |
|---|---|
| `./lekiwi basic` | 바닥·조명·중력이 있는 실습대. 큐브를 직접 생성 |
| `./lekiwi basic --lesson drop` | 세 큐브의 물리 설정 차이 확인 |
| `./lekiwi basic --lesson mass` | 0.1 kg / 1 kg 큐브의 낙하 비교·중력 변경 |
| `./lekiwi basic --lesson friction` | 15° 경사로 두 개에서 마찰 비교 |
| `./lekiwi basic --lesson bounce` | 반발력 0 / 0.8인 공과 받침 비교 |
| `./lekiwi basic --lesson basket` | 바닥·네 벽으로 만든 열린 바구니에 큐브 낙하 |
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
```

Docker 내부의 실제 PhysX로 낙하, 질량 비교, 경사로 마찰, 반발력 차이,
바구니 안착과 교육용 관절의 양방향 추종·60° 제한을 확인합니다. 성공 시 마지막에 `ISAACSIM_BASIC_TEST result=PASS`가 출력됩니다.
이 명령은 결과 확인용이며 GUI 버튼 실습을 대신하지 않습니다.

각 편의 `SOURCES.md`에 출처와 실제 검증 범위를 기록합니다. 전체 결과는 [검증 기록](VALIDATION.md)을 참고하세요.


## 파일 구조와 보는 방법

```text
isaacsim_basic/
  README.md                       전체 목차
  01_object_physics/               2~4편도 동일 구조
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
2. 노션에서 **설정 → 가져오기(Import) → ZIP**을 선택하거나 `/zip`의 가져오기 기능을 사용합니다.
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
