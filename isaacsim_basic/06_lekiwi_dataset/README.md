# 6편 · 코드로 이해하는 LeKiwi RGB·상태·명령 수집

이 장은 실제 LeKiwi 시뮬레이션에서 시연을 수집합니다. 5장의 한 관절 예제와 구분합니다.
카메라 수집·시간 연결·저장 요청의 실제 구현을 [01_lekiwi_recording.py](experiments/01_lekiwi_recording.py)에서 읽습니다.
이 파일은 프로젝트의 로봇 자산, EpisodeWorker와 데이터 형식을 사용하므로 **저장소 전체가 필요합니다.**

## 실행·수정 순서

저장소 루트의 터미널에서 실행합니다. 설치를 마친 PC라면 먼저 `./lekiwi setup sim`으로 교재 런타임을 빌드합니다.
`experiments/`의 Python 파일은 Docker 안에 읽기 전용으로 연결되므로 **호스트에서 코드를 저장하면 다음 실행에 반영됩니다.** 코드만 수정할 때 이미지 재빌드는 필요 없습니다.

1. 이 장의 Python 파일을 편집기로 열고 기본 코드를 읽습니다.
2. 결과를 먼저 예상하고 실행합니다. 객체·속성은 기본 **Stage / Property**, 장면은 **Viewport**에서 확인합니다.
3. Isaac Sim 창을 닫고 터미널로 돌아온 것을 확인합니다.
4. 교재가 지정한 기본 줄에 `#`를 붙이고 다음 줄의 `#`를 지웁니다. 들여쓰기는 유지합니다.
5. 파일을 저장하고 같은 명령으로 재실행하여 결과를 비교합니다.

코드를 수정해도 이미 열린 장면은 바뀌지 않습니다. 같은 실행을 반복할 때는 코드 재실행과 표준 타임라인의 **Stop → Play**를 구분합니다.
Play는 실행, Pause는 현재 위치에서 일시정지, Stop은 실행 전 상태로 돌아갑니다. Python 수정은 창을 닫고 재실행해야 반영됩니다.


## 1. 실행과 기본값 수정

```bash
./lekiwi basic --chapter 6
```

`./lekiwi record`도 같은 기록 코드를 사용합니다. 처음에는 실물 리더 없이 키보드로 짧은 직진·정지를 기록합니다.
좌측 Perspective / 우측 front 화면이 열립니다. 별도 기록 탭은 없습니다.
터미널에서 `LEKIWI_RECORD state=READY`까지 기다립니다.

![전용 탭 없는 LeKiwi 기록 화면](images/09-code-first.png)

`RecordingPanel`은 이전 코드와의 호환을 위한 클래스 이름이며 UI 창을 만들지 않습니다.
생성자에서 다음 부분을 찾아 기본 30초 줄 대신 120초 또는 0 줄을 활성화합니다.

```python
self.duration_seconds = 30
# self.duration_seconds = 120
# self.duration_seconds = 0
```

0은 무제한이며 F6으로 끝냅니다. 시간은 시뮬레이션 시간 기준입니다.
파일 수정 없이 실행별 값을 지정하려면 다음처럼 합니다. 환경변수 값이 코드 기본값보다 우선합니다.

```bash
LEKIWI_RECORD_SECONDS=120 ./lekiwi record
```

집기 과제로 바꿀 때는 `self.task_text = "Move a block to its matching basket"` 줄을 주석 해제하거나
`LEKIWI_RECORD_TASK` 환경변수에 같은 작업 설명을 전달합니다. 같은 의미의 시연에는 일관된 설명을 사용합니다.

## 2. 영상이 만들어지는 코드

```python
product = rep.create.render_product(camera_path, resolution)
rgb = rep.AnnotatorRegistry.get_annotator("rgb")
rgb.attach([product.path])
rgba = np.asarray(rgb.get_data())
```

실제 파일은 front·wrist 각각에 Render Product와 RGB annotator를 연결합니다.
`get_data()`의 결과는 최신 도착 영상입니다. **현재 물리 스텝과 같은 시각이라고 가정하면 안 됩니다.**

`snapshot()`은 ReferenceTime을 카메라의 실제 시뮬레이션 촬영 시각으로 바꾸고 두 카메라의 시각이 같은지 검사합니다.
`before_step()`은 상태·명령을 보관하고, `after_step()`은 다음 상태를 연결합니다.
`accept_capture()`가 늦게 도착한 RGB를 원래 촬영 시각의 상태·명령에 연결합니다.
이 교재의 기록 실행은 렌더 완료를 기다리는 동기 설정을 사용합니다. 명령 전 t의 영상을 잠시 보관하고, 물리 스텝 후 t+dt 상태와 합쳐 저장합니다.
지연 영상도 촬영 시각으로 검사합니다. 매 프레임 타임라인 Pause/Play를 반복하지 않습니다.

다음 읽기 과제: `world.current_time`으로 모든 영상 시각을 덮어쓰면 왜 학습 데이터가 잘못될 수 있는지 설명합니다.
시간 검사는 삭제하지 말고 의미를 읽습니다.

## 3. 기록·저장·폐기

Viewport를 클릭한 상태에서 한 번씩 누릅니다. 파일 작업은 키 콜백이 아닌 주 반복문에서 처리합니다.

| 키 | 동작·조건 |
|---|---|
| F5 | READY / SAVED / DISCARDED에서 새 기록 시작 |
| F6 | 수집 종료 요청. 마지막 영상·파일 쓰기가 끝나면 UNSAVED |
| F7 | UNSAVED 기록을 실패·연습(success=false)으로 저장 |
| F9 | UNSAVED 기록을 성공(success=true)으로 저장 |
| F10 두 번 | 3초 안에 두 번 눌러 이번 미저장 기록 폐기 |
| F8 | 저장·폐기 완료 후 로봇 초기화·라인별 큐브 재배치 |
| SPACE | 로봇 주행·가상 팔 추종 정지. 파일 수집은 별도로 F6 |

1. READY를 확인하고 F5를 누릅니다.
2. 짧게 W로 전진한 뒤 이동키를 모두 놓고 SPACE로 정지합니다.
3. F6을 누릅니다. FINISHING 동안 마지막 RGB와 파일 쓰기를 기다립니다.
4. UNSAVED에서 결과를 검토하고 F7 또는 F9를 누릅니다.
5. `SAVING → SAVED`와 `LEKIWI_RECORD saved=... frames=...`를 확인합니다.

성공 표시는 자동 판정이 아닙니다. 실제 과제를 완료했을 때만 F9를 사용합니다.
F10은 이미 저장된 에피소드를 지우지 않습니다. 기록 중 Pause/Stop은 시간 연결 오류가 되므로 해당 take를 폐기하고 새로 시작합니다.
F8은 미저장·기록·저장 진행 중에 차단됩니다. 완료 후 재배치하고 리더 사용 시 R을 다시 누릅니다.

## 4. 원본 파일과 시간 순서

```text
/data/recordings/lekiwi.XXXXXXXX/
  episode.XXXXXXXX/
    manifest.json
    frames.jsonl
    images/front/
    images/wrist/
```

정확한 파일·카메라 경로는 manifest에 기록됩니다. `.partial`은 미완료이며 완성 데이터로 쓰지 않습니다.
한 프레임은 관측 상태 t, 두 RGB t, action t, 후속 상태 t+1/30초를 담습니다.
팔 6개 관절은 rad, 베이스 명령은 m/s·rad/s이며 순서는 manifest의 feature 설명을 따릅니다.
카메라 장착·보정값, 초기 코스, 작업 설명, 성공 여부도 manifest에 남깁니다.

PNG 저장은 백그라운드에서 수행합니다. 저장이 밀리거나 RGB 프레임이 빠지면 ERROR로 중단합니다.
프레임을 조용히 생략한 데이터셋을 만들지 않습니다. 터미널 오류와 저장 공간을 확인한 뒤 새로 수집합니다.

## 5. LeRobot 데이터셋으로 변환하기

필요한 기록을 저장한 뒤 Isaac Sim을 닫고 종료를 기다립니다.
아래 `lekiwi.XXXXXXXX`를 **터미널의 LEKIWI_RECORD directory에 나온 실행 폴더**로 바꾸고 출력 폴더는 아직 없는 새 이름을 사용합니다.

```bash
./lekiwi export-dataset \
  --input /data/recordings/lekiwi.XXXXXXXX \
  --output /data/datasets/lekiwi_lesson6_01 \
  --repo-id local/lekiwi_lesson6
```

한 실행 폴더의 완료된 에피소드를 묶습니다. `--input`에 저장된 `episode.<ID>` 폴더 하나만 지정할 수도 있습니다.
`--success-only`를 붙이면 사용자가 성공으로 표시한 기록만 선택합니다. 기본값은 연습·성공 기록을 모두 포함합니다.
출력 폴더가 이미 있으면 덮어쓰지 않고 종료합니다. 카메라 장착값이나 해상도가 다른 기록은 한 데이터셋으로 섞지 않습니다.

![변환 후 실제 검사 결과](images/06-export.png)

이 터미널 이미지는 앞서 검증한 **2개 에피소드·19프레임**의 별도 변환 예시입니다. 위에서 새로 촬영한 40프레임 기록의 변환 결과는 아닙니다.

변환은 LeRobot 이미지에서 수행합니다. 호스트에 LeRobot을 설치하지 않고 GitHub/Hugging Face 업로드도 수행하지 않습니다.
PNG를 두 카메라 영상으로 인코딩하고 상태·행동은 Parquet, 에피소드·feature 정보는 meta 아래에 저장합니다.

```text
data/datasets/lekiwi_lesson6_01/
  data/                 상태·행동 Parquet
  videos/               front·wrist 영상
  meta/                 feature·통계·에피소드 정보
  recording_report.json 변환 완료·입력 출처·카메라 설정·검사 결과
```

`LEKIWI_DATASET result=PASS`와 에피소드 수·총 프레임 수를 확인합니다.
변환 중 오류가 나면 `recording_report.json`의 완료 표시가 없습니다. 해당 출력은 완성된 데이터셋으로 사용하지 않습니다.
원본 에피소드를 확인한 뒤 새 출력 폴더로 다시 변환합니다.

변환기는 LeRobot의 `finalize()`로 파일을 닫고 다시 열어 프레임 수를 비교합니다.
각 에피소드의 처음·중간·마지막에서 실제 관측·행동과 두 영상의 디코딩을 검사합니다.
이는 **파일 검증**이며, 로봇을 움직여 같은 동작을 재현하는 물리 재생이나 정책 성능 검증은 아닙니다.
원본 JSON에는 후속 상태·카메라 시각도 남기고, LeRobot 학습 feature에는 관측 상태·두 RGB·행동을 전달합니다.


## 6. 리더 시연과 로컬 학습으로 연결

[4편](../04_teleoperation/README.md)의 장비 준비·보정을 끝낸 뒤 기존 시뮬레이터를 닫습니다.
본인 USB 경로로 다음을 실행합니다. 실물 장비의 안전 확인은 한 단계씩 수행합니다.

```bash
LEKIWI_RECORD_SECONDS=120 ./lekiwi teleop \
  --port /dev/serial/by-id/usb-본인_SO101_장치 \
  --id so101_leader --scene random --record
```

기록 옵션이 리더를 자동 활성화하지 않습니다. R 활성화 뒤 같은 F5/F6/F7/F9 키를 사용합니다.
리더 시연을 충분히 모으고 변환이 PASS인 로컬 데이터셋으로 학습합니다. Hugging Face 업로드는 수업에 포함하지 않습니다.
학습·추론 명령은 [프로젝트 README](../../README.md)와 [로컬 데이터 관리](../../docs/dataset-manager.md)를 따릅니다.
짧은 저장 검사를 통과했다는 사실과 충분한 학습 데이터·정책 성능을 구분합니다.

완료 기준: [기록지](worksheet.md)에 수집 시간·프레임 수·성공 여부·저장 경로·변환 결과를 남깁니다.

[공식 자료](SOURCES.md) · [전체 목차](../README.md)
