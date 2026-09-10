# Isaac Sim Basic · Python으로 배우는 1~6편

객체 물리 → 관절 → 카메라 → 입력·조작 → 관절 기록 → LeKiwi 데이터셋 순서입니다.
**Python 코드 읽기 → 실행 → 주석 교체 → 저장·재실행 → 결과 비교**로 수업합니다.
Isaac Sim 안에 전용 Lesson 탭을 만들지 않습니다. 기본 Stage·Property·Viewport·Play/Stop을 사용합니다.

객체·환경·물리 설정 API에는 줄별 한국어 설명과 단위를 적었습니다.
각 장의 `experiments/` 파일에 기본 코드와 주석 처리된 다음 단계가 함께 있습니다.

## 교재와 실행

| 편 | 교재 | 시작 명령 | ZIP |
|---|---|---|---|
| 1 | [객체·중력·충돌·질량·마찰·반발](01_object_physics/README.md) | `./lekiwi basic --chapter 1` | [노션](01_object_physics/01_object_physics_notion.zip) |
| 2 | [관절과 Drive](02_robot_joints/README.md) | `./lekiwi basic --chapter 2` | [노션](02_robot_joints/02_robot_joints_notion.zip) |
| 3 | [Camera API와 LeKiwi TF](03_robot_cameras/README.md) | `./lekiwi basic --chapter 3` | [노션](03_robot_cameras/03_robot_cameras_notion.zip) |
| 4 | [관절 입력과 teleop](04_teleoperation/README.md) | `./lekiwi basic --chapter 4` | [노션](04_teleoperation/04_teleoperation_notion.zip) |
| 5 | [관절 JSON 기록·재생](05_data_recording/README.md) | `./lekiwi basic --chapter 5` | [노션](05_data_recording/05_data_recording_notion.zip) |
| 6 | [LeKiwi RGB·상태·명령 수집](06_lekiwi_dataset/README.md) | `./lekiwi basic --chapter 6` | [노션](06_lekiwi_dataset/06_lekiwi_dataset_notion.zip) |

각 편에는 README.md, worksheet.md, SOURCES.md, experiments/*.py, images/, 노션 ZIP이 있습니다.
5편은 에피소드 구조를 배우는 한 관절 예제입니다. 본격적인 LeKiwi 데이터 수집·변환은 6편에서 진행합니다.
실물 리더는 4·6편의 선택 실습에서만 필요합니다.

## 설치 후 처음 실행하기

프로젝트 [설치 순서](../README.md)를 마친 Ubuntu PC에서 저장소 루트의 터미널을 사용합니다.

```bash
export ACCEPT_EULA=Y
./lekiwi setup sim
./lekiwi basic --chapter 1
```

이 개편을 받아 처음 실행할 때는 런타임 이미지 빌드가 필요합니다.
이후 학생 Python 파일만 수정할 때는 저장 후 같은 명령을 실행하면 됩니다. 해당 폴더가 Docker에 읽기 전용으로 연결됩니다.

구체적인 파일을 지정할 수도 있습니다.

```bash
./lekiwi basic --script 01_object_physics/experiments/01_no_gravity.py
```

1장 비교 파일은 `--experiment 1`부터 `--experiment 6`까지입니다. **실험 번호와 교육 장 번호는 별개**입니다.
이전 `--lesson joints`, `--lesson recording`은 각각 2·5장 새 학생 파일로 연결됩니다.
빈 장면과 바구니 보충 실습은 `--lesson blank`, `--lesson basket`입니다.
선택용 `./lekiwi classroom`은 같은 명령을 여는 외부 실행기이며 수업은 터미널·소스 편집을 기준으로 합니다.

## 코드 수정과 기본 UI

1. 편집기에서 해당 Python 파일을 엽니다.
2. 기본 실행의 결과를 예측합니다.
3. 실행하여 기본 Stage/Property에서 값과 객체를 확인합니다.
4. Isaac Sim 창을 닫고 실행 종료를 기다립니다.
5. 지정된 기본 줄을 주석 처리하고 다음 줄을 해제합니다. 들여쓰기를 유지하고 파일을 저장합니다.
6. 같은 명령으로 다시 실행합니다.

1~3장 기본 예제는 정지 상태로 열려 표준 Play를 누릅니다.
4장은 가상 관절 입력을 즉시 받으며 J/L/K로 목표를 보냅니다. 5장은 3초 기록 후 멈춥니다.
6장은 LeKiwi를 계속 시뮬레이션하며 F5/F6/F7/F9로 기록을 관리합니다.

| 상황 | 반복 방법 |
|---|---|
| 1~3장 같은 설정 재실험 | 기본 Stop → Play |
| Python 설정 수정 | 창 닫기 → 저장 → 같은 명령 재실행 |
| LeKiwi 큐브를 다시 배치 | Viewport에서 F8. 기록 중에는 저장·폐기부터 완료 |
| 5장 추가 기록·재생 | 학생 파일에서 record/replay 호출을 선택하고 재실행 |

LeKiwi의 키보드·기록 단축키는 프로젝트 코드가 등록합니다. 기본 Isaac Sim 단축키와 구분해 교재에 표시했습니다.

## 일반 Isaac Sim 설치에서 사용하기

1~5장의 학생 파일은 프로젝트 helper·로봇 자산 없이 Isaac Sim 5.1 Python으로 실행할 수 있습니다.
Isaac Sim 설치 폴더에서 `./python.sh /절대경로/학생파일.py`를 실행합니다.
실행 현재 폴더에 결과를 쓰므로 쓰기 권한이 있는 폴더에서 설치된 python.sh의 절대 경로를 호출해도 됩니다.
호스트 일반 Python에는 `omni`와 `pxr`가 없으므로 `python 학생파일.py`로 대신하지 않습니다.

6장은 프로젝트 로봇 자산·시간 동기 검사·EpisodeWorker를 사용하므로 저장소가 필요합니다.
Docker의 `/data`는 호스트 `data`에 연결됩니다. 컨테이너 종료 후에도 저장된 실습 결과·데이터셋·보정 파일이 유지됩니다.

## 노션 가져오기

장별 ZIP은 HTML과 실제 PNG를 포함합니다. 노션 `Import > HTML`에서 가져옵니다.
Markdown은 GitHub 또는 편집기의 Markdown Preview에서 읽습니다. 다른 장·Python 파일은 저장소 링크로 확인합니다.
원본 스크린샷 위에 빨간 사각형을 추가하며 실제 버튼이나 화면 내용을 합성하지 않습니다.

## 수업 시간 계획

코드 읽기·수정·비교를 포함한 **계획용 추정**입니다. 실제 반의 Python 경험과 GPU에 따라 달라집니다.

| 편 | 예상 |
|---|---|
| 1 | 120~150분 |
| 2 | 75~90분 |
| 3 | 75~90분 |
| 4 | 코드·키보드 60~75분, 리더 선택 실습 60~90분 추가 |
| 5 | 75~90분 |
| 6 | 키보드 수집·변환 90~120분, 리더 수집 30~60분 추가 |

실물 없이 8시간 15분~10시간 15분, 리더 포함 9시간 45분~12시간 45분의 실습 시간입니다.
휴식·질문을 포함해 2일 14~16시간 편성을 예상합니다. 최초 설치·충분한 시연 확보·학습 시간은 별도입니다.

[검증 기록](VALIDATION.md) · [프로젝트 전체 흐름](../README.md)
