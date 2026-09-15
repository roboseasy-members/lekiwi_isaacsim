# Isaac Sim Basic · 환경 설정·직접 제작·Python 실습 0~6장

환경 설정 → 객체 물리 → 관절 → 카메라 → 입력·조작 → 관절 기록 → LeKiwi 데이터셋 순서입니다.
**처음 수업을 시작한다면 [0장 환경 설정](00_env_setting/README.md)부터 진행합니다.**
학생별 Ubuntu NVIDIA GPU 노트북 한 대에서 VS Code 설치·GPU와 Docker 준비·이미지 빌드를 직접 진행하고,
실행 검사와 Isaac Sim 창·Play 조작을 확인한 뒤 1장으로 넘어갑니다. 리더암 USB도 같은 노트북에 연결합니다.
**화면에서 직접 제작 → 속성을 바꾸며 관찰 → 같은 구성을 Python으로 제작 → 두 결과 비교**로 수업합니다.
Isaac Sim 안에 전용 Lesson 탭을 만들지 않습니다. 기본 Stage·Property·Viewport·Play/Stop을 사용합니다.

각 장의 **README 한 문서를 처음부터 끝까지** 읽습니다. 먼저 메뉴·속성·스크린샷을 따라 실험하고 저장합니다.
API 이름·Python 파일·코드 실행과 수정은 각 장의 마지막 ‘같은 작업을 코드로 구현하기’ 절에서 다룹니다.
기록지도 마우스 실습 → 코드 실습 → 두 결과 비교 순서로 작성합니다.

## 교재 읽는 순서

| 장 | 본문 | 먼저 마우스로 하는 일 | 마지막 코드 실습 | 노션 ZIP |
|---|---|---|---|---|
| 0 | [환경 설정](00_env_setting/README.md) | VS Code 설치·환경 준비·이미지 빌드·창·Play 확인 | 환경 준비 단계 | [노션](00_env_setting/00_env_setting_notion.zip) |
| 1 | [객체와 물리](01_object_physics/README.md) | 바닥·물체 생성, 중력·충돌·질량·마찰·반발 실험 | 같은 여섯 물리 실험 구현 | [노션](01_object_physics/01_object_physics_notion.zip) |
| 2 | [관절과 모터](02_robot_joints/README.md) | 받침·팔·관절·Drive 제작, 목표 각도 비교 | 같은 모형과 응답 구현 | [노션](02_robot_joints/02_robot_joints_notion.zip) |
| 3 | [카메라와 시점](03_robot_cameras/README.md) | Camera 생성, 렌즈·자세·부모 변경 | 같은 카메라와 LeKiwi 좌표 이해 | [노션](03_robot_cameras/03_robot_cameras_notion.zip) |
| 4 | [관절 조작과 입력](04_teleoperation/README.md) | 저장한 관절 USD에서 목표 입력·Play | 본인 USD에 키보드 제어 연결, LeKiwi·리더 확장 | [노션](04_teleoperation/04_teleoperation_notion.zip) |
| 5 | [장면 저장과 움직임 기록](05_data_recording/README.md) | 관절 확인·직접 조작·USD 저장 | 본인 USD의 JSON 기록·재생 | [노션](05_data_recording/05_data_recording_notion.zip) |
| 6 | [LeKiwi 데이터 수집](06_lekiwi_dataset/README.md) | 로봇 자산·큐브·바구니·관찰 카메라 구성 | 준비된 환경의 RGB·상태·명령 수집·변환·ACT | [노션](06_lekiwi_dataset/06_lekiwi_dataset_notion.zip) |

1~6장에는 본문 README, 기록지 worksheet, 출처 SOURCES, 학생 Python, 실제 화면과 노션 ZIP이 있습니다.
기존 `gui.md` 링크는 통합된 본문으로 안내합니다. 별도 직접 제작 문서를 먼저 찾아갈 필요가 없습니다.
실물 리더는 4·6장의 선택 실습에서만 필요합니다.

## 첫 실습은 빈 편집 화면에서 시작하기

[0장](00_env_setting/README.md)의 확인용 창을 닫고 **노트북의 저장소 루트 터미널**에서 실행합니다.

```bash
./lekiwi basic --script 01_object_physics/experiments/00_empty_stage.py
```

이미 빈 화면을 열었다면 중복 실행하지 않습니다. 객체는 [1장](01_object_physics/README.md)에서 직접 만듭니다.

일반 Isaac Sim 5.1 설치에서는 앱을 열고 `File > New`로 시작할 수 있습니다.
1장에서 만든 `base_scene.usda`는 2·3·6장의 시작 장면으로, 2장의 `my_joint.usda`는 4·5장의 관절 모형으로 재사용합니다.
새 실험을 시작할 때는 `Save As`로 새 이름을 사용해 기준 파일을 보관합니다.

## 장 마지막의 코드 실습 실행 참고

아래 명령은 각 장의 마우스 실습과 저장을 마친 뒤 사용합니다.

| 장 | 같은 노트북의 저장소 루트 터미널 |
|---|---|
| 1 | `./lekiwi basic --chapter 1` |
| 2 | `./lekiwi basic --chapter 2` |
| 3 | `./lekiwi basic --chapter 3` |
| 4 | `./lekiwi basic --chapter 4` |
| 5 | `./lekiwi basic --chapter 5` |
| 6 | `./lekiwi basic --chapter 6` |

1장 비교 파일은 `--experiment 1`부터 `--experiment 6`입니다. 실험 번호와 장 번호는 다릅니다.
Python을 수정할 때는 실행 종료 → 코드 저장 → 같은 명령 재실행 순서로 진행합니다.
실행 종료는 Isaac Sim 창 닫기입니다. 저장·폐기 작업을 마치고 종료합니다.

학생 파일의 객체·물리 설정 줄에는 한국어 설명과 단위, 주석 처리된 비교 예제가 있습니다.
호스트에서 저장한 파일은 다음 실행에 반영되며, 코드만 수정할 때 Docker 이미지 재빌드는 필요 없습니다.
GUI에서 USD를 저장해도 Python 소스가 자동 수정되지는 않습니다.

1~3장 코드는 정지 상태로 열리므로 Play를 누릅니다. 4장은 J/L/K 입력을 받고, 5장은 자동으로 3초간 기록합니다.
6장은 F5/F6/F7/F9로 기록을 관리합니다. 이런 키는 프로젝트가 등록한 기능이며 기본 Isaac Sim의 장면 저장과 구분합니다.
6장 기록기는 직접 저장한 임의 USD를 자동으로 읽지 않습니다. 준비된 전체 코스와 동기화된 두 카메라 환경을 사용합니다.

## 일반 Isaac Sim 설치에서 사용하기

1~5장의 학생 파일은 프로젝트 helper·로봇 자산 없이 Isaac Sim 5.1 Python으로 실행할 수 있습니다.
Isaac Sim 설치 폴더에서 `./python.sh /절대경로/학생파일.py`를 실행합니다.
실행 현재 폴더에 결과를 쓰므로 쓰기 권한이 있는 폴더에서 설치된 python.sh의 절대 경로를 호출해도 됩니다.
호스트 일반 Python에는 `omni`와 `pxr`가 없으므로 `python 학생파일.py`로 대신하지 않습니다.

6장은 프로젝트 로봇 자산·시간 동기 검사·EpisodeWorker를 사용하므로 저장소가 필요합니다.
Docker의 `/data`는 호스트 `data`에 연결됩니다. 컨테이너 종료 후에도 저장된 실습 결과·데이터셋·보정 파일이 유지됩니다.

## 노션 가져오기

장별 ZIP을 노션 `Import > HTML`에서 가져온 뒤 **README 페이지**부터 읽습니다. 0장은 교재·기록지·출처 HTML, 1~6장은 HTML과 실제 PNG를 포함합니다.
Markdown은 GitHub 또는 편집기의 Markdown Preview에서 읽습니다. 다른 장·Python 파일은 저장소 링크로 확인합니다.
원본 스크린샷 위에 빨간 사각형을 추가하며 실제 버튼이나 화면 내용을 합성하지 않습니다.

## 수업 시간 계획

아래는 기존 코드 실습 기준의 **계획용 추정**입니다. 새로 추가한 직접 제작·사진 기록 시간은 포함하지 않으며 리허설에서 다시 측정합니다.

| 편 | 예상 |
|---|---|
| 1 | 120~150분 |
| 2 | 75~90분 |
| 3 | 75~90분 |
| 4 | 코드·키보드 60~75분, 리더 선택 실습 60~90분 추가 |
| 5 | 75~90분 |
| 6 | 키보드 수집·변환 90~120분, 리더 수집 30~60분 추가 |

실물 없이 8시간 15분~10시간 15분, 리더 포함 9시간 45분~12시간 45분의 실습 시간입니다.
휴식·질문을 포함해 2일 14~16시간 편성을 예상합니다. 위 추정에는 0장 최초 설치·빌드, 충분한 시연 확보·학습 시간이 포함되지 않습니다.
0장을 수업 중 학생이 직접 진행하므로 설치 시간을 따로 배정합니다. 총 6시간으로 진행할 때는 다운로드·재부팅 소요 시간에 따라 이후 실습 범위를 줄여야 합니다.

[검증 기록](VALIDATION.md) · [프로젝트 전체 흐름](../README.md)
