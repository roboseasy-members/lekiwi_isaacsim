# 1~6편 검증 기록

1~4편 검증일: 2026-09-07. 5·6편과 전체 재점검은 문서 하단의 2026-09-08 기록을 참고하세요. 대상: 이 저장소의 Isaac Sim 5.1.0 Docker 이미지와 Ubuntu 데스크톱.

## 교재와 패키지

- 4개 편별 폴더에 README.md, worksheet.md, SOURCES.md, images/, 노션 ZIP을 구성했습니다.
- 실제 화면 27장: 1편 11장, 2편 5장, 3편 7장, 4편 4장. 별도로 1편 개념도 1장.
- 원본 PNG와 SVG에 포함된 PNG의 바이트 일치·SHA256, 빨간 사각형의 화면 범위 검사를 통과했습니다.
- 강조 PNG 렌더링을 확인했습니다. 원본 UI 텍스트를 합성하거나 생성형 이미지로 재구성하지 않았습니다.
- Markdown의 로컬 파일 링크, 노션 ZIP의 HTML/PNG 상대 링크와 ZIP 무결성을 검사했습니다.
- ZIP은 교재·기록지·출처 HTML과 참조하는 PNG만 포함합니다. 실물 보정 파일·세션 로그·ROS 파일은 넣지 않습니다.
- 실제 노션 계정으로 가져오는 테스트는 미실시입니다. 공식 지원 형식인 HTML·PNG ZIP으로 준비했습니다.

## 자동 검사

```bash
PYTHONPATH=/tmp/lekiwi-camera-usd PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests isaacsim_basic/test_scenes.py
```

개발 PC에서 임시 설치한 USD로 **193 passed, 1 skipped**였습니다.
위 `/tmp` 경로는 제작 PC 검증 환경이며 교육생 설치 절차가 아닙니다.
일반 교육생은 아래 Docker 검사를 사용합니다. 호스트 Python에 Isaac Sim을 설치할 필요가 없습니다.
Python/Bash 구문 검사와 `git diff --check`도 통과했습니다.

| 검사 | 확인 내용 | 결과 |
|---|---|---|
| `./lekiwi test-basic` | 낙하, 질량, 마찰, 반발력, 바구니, 한 관절 모형 | PASS |
| 관절 모형 +30° | 실제 도달각 | 29.999° |
| 관절 모형 -30° | 실제 도달각 | -30.000° |
| 관절 모형 80° | 상한 60° 제한 | 60.000° |
| `./lekiwi test-arm` | SO101 6개 관절, 기본 자세, 절대각·지연·오래된 입력 처리 | PASS |
| 6개 관절 개별 추종 | 최대 목표 오차 | 약 0.0018 rad |
| 30 FPS 가상 입력 추종 | 목표 오차 | 약 0.0005 rad |
| `./lekiwi test-physics` | 바퀴 접촉 기반 전진·좌측 평행이동·반시계 회전 | PASS |
| 베이스 이동 결과 | 전진 / 좌측 / 회전 | 0.22832 m / 0.23298 m / 0.78453 rad |

이 검사는 실제 PhysX를 사용하지만 실제 SO101 USB·모터를 사용하지 않습니다.
실물 리더의 방향·영점, 실제 TF, 집기 성공은 별도의 사용자 확인 항목입니다.

## 실제 GUI에서 확인한 내용과 제한

- 2편: Stage 구조, 관절 앵커·축·상하한·Drive, Ctrl+클릭 숫자 입력, 30° Play/Pause 결과.
- 3편: C 시점 전환, Camera/optical frame 속성, Create Camera 메뉴, Focal Length 2배 비교와 복구.
- 4편: 가상 베이스 W 전진·정지, 1/2 속도 선택, T 추적 시점.
- 손목 카메라는 기본 자세에서 팔 부품에 크게 가립니다. 3편은 이 화면을 가림 진단 예로 사용합니다.
  실제 TF 측정 후 렌즈 중심·정면·부착 링크를 맞추고 여러 자세에서 재검증해야 합니다.
- 현재 실행의 전역 조작키가 속성 입력 중에도 반응하는 경우가 있어, 3편의 속성 편집은 먼저 Pause하도록 안내합니다.
- Space가 Isaac 기본 재생 단축키와 함께 Pause를 일으킬 수 있어, 4편은 재개 전 Play 상태를 확인하도록 안내합니다.
  이 제작 범위에서는 기존 조작 런타임을 변경하지 않았습니다.
- 카메라 동기화·고정 해상도 데이터셋 녹화·학습·정책 실행은 이번 1~4편 범위에 포함하지 않습니다.


## 5편 · 2026-09-08

5편은 한 관절 모형으로 에피소드·관측·행동·시간 대응을 배우는 기초 실습입니다.
이 5편 검증 당시 LeKiwi + SOARM의 영상 포함 녹화는 후속 범위였으며, 이후 6편에서 수집·변환을 구현했습니다. 학습은 별도입니다.

- 실제 GUI에서 READY → RECORDING → UNSAVED → SAVED → REPLAYING → REPLAYED를 확인했습니다.
- 60 Hz 시뮬레이션 시간으로 180프레임·3초를 기록하고 JSON을 저장한 뒤 다시 읽어 재생했습니다.
- 자동 PhysX 검사와 실제 GUI 재생에서 최대 상태 오차 0 rad를 확인했습니다. 다른 환경의 동일 결과를 보장하지 않으며 자동 기준은 0.01 rad 미만입니다.
- GUI에서 Discard unsaved로 새 기록을 버린 뒤 기존 파일의 SHA256이 유지되는 것을 확인했습니다.
- 새 기록을 저장하면 기존 에피소드와 다른 폴더에 180프레임이 저장되는 것을 확인했습니다.
- 자동 검사는 빈 기록·누락 스텝·비정상 수치·관측 짝 불일치·시간 간격 오류를 거부합니다.
- 전체 자동 검사: 201 passed, 1 skipped. 건너뛴 항목은 호스트의 xacro 미설치에 따른 URDF 재생성 검사입니다.
- 화면 6장의 원본 PNG·SVG 사각형·강조 PNG를 작성했습니다. 커서가 버튼과 수치를 가리지 않는지 화면으로 확인했습니다.
- 교재·기록지·출처 HTML과 참조 PNG를 담은 5편 노션 ZIP을 제공합니다. 실제 노션 가져오기는 미실시입니다.
- 5편에서는 USB를 열거나 실물 모터를 조작하지 않았습니다.

```bash
./lekiwi basic --lesson recording  # GUI 실습
./lekiwi test-recording            # Docker 내부 PhysX 검사
```

호스트 자동 검사 재현(제작 PC 임시 USD 환경):

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/lekiwi-camera-usd PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  python -m pytest -q -p no:cacheprovider tests isaacsim_basic/test_scenes.py isaacsim_basic/test_recording.py
```


## 실습 창 자동 배치 · 2026-09-08

- 1~5편의 창 생성 경로를 점검했습니다. 1·2편에는 사용자 정의 안내 창이 없으며 Stage / Property를 사용합니다.
- 3·4편 공통 조작 창과 5편 기록 창에 `deferred_dock_in("Stage", CURRENT_WINDOW_IS_ACTIVE)`를 적용했습니다.
  Stage가 준비되면 같은 영역에 실습 탭을 만들고 해당 탭을 먼저 표시합니다.
- 실제 GUI에서 두 종류 창의 자동 배치와 Stage 탭 왕복 전환을 확인했습니다.
- 공통 조작 창은 실물 연결 없는 `sim`에서 전방·손목·추적 시점, 베이스 전진·정지·속도 전환을 확인했습니다.
  `teleop`도 같은 창 생성 코드를 사용하며, 이번 UI 변경 검증에서 실물 리더 연결은 실행하지 않았습니다.
- 5편은 도킹된 창에서 180프레임 기록·저장·재생을 확인했고 최대 상태 오차는 0 rad였습니다.
- 3편의 시점 화면 3장, 4편 4장, 5편 6장을 다시 캡처하고 빨간 표시와 노션 ZIP을 갱신했습니다.
- 관련 자동 검사: `tests/test_deployment.py`, `tests/test_drive_controls.py`, `isaacsim_basic/test_recording.py` — 42 passed, 1 skipped.
- 교재 상대 링크 67개, 원본과 SVG에 포함된 이미지 33장, 5개 ZIP의 내부 링크·무결성 검사와 `git diff --check`를 통과했습니다.

API 근거: [NVIDIA Window 도킹 안내](https://docs.omniverse.nvidia.com/dev-guide/latest/programmer_ref/ui/widgets/window.html),
[omni.ui.Window API](https://docs.omniverse.nvidia.com/kit/docs/omni.ui/latest/omni.ui/omni.ui.Window.html).
실제 설치된 Isaac Sim 5.1의 `omni.ui` 타입 정의에서도 메서드와 DockPolicy 값을 확인했습니다.


## 6편 · LeKiwi 영상·명령 수집 · 2026-09-08

- `./lekiwi record`는 실물 연결 없이 기존 가상 로봇·코스에 6편 기록 창을 추가합니다.
- 전방·손목 RGB 640×480을 같은 물리 상태에서 동기 캡처합니다. delta_time=0 캡처 동안 물리 스텝·시각 불변과 두 render reference 일치를 검사합니다.
- 물리 계산은 기존 120 Hz를 유지하고, 기록 모드의 관측·행동 간격은 30 Hz입니다. 일반 sim/teleop의 60 Hz 렌더 루프는 유지합니다.
- 실제 GUI에서 READY → RECORDING → UNSAVED → SAVED, 새 기록 → DISCARDED를 확인했습니다. 저장본은 유지됐습니다.
- 전진·정지 기록 11프레임과 연습 기록 8프레임을 저장했습니다. 성공 기록의 베이스 +X 이동은 약 0.036 m이며 마지막 베이스 명령은 0입니다.
- 총 19프레임의 관측·행동·후속 상태, 38개 원본 PNG의 시간·크기·SHA256 검사를 통과했습니다.
- LeRobot 0.6.1 이미지에서 두 에피소드를 변환한 뒤 finalize와 재열기를 완료했습니다. 각 에피소드의 처음·중간·마지막 관측·행동 및 두 영상 디코딩을 검사했습니다.
- `--success-only` 변환은 성공으로 표시한 11프레임만 선택했습니다.
- 전체 자동 검사 215 passed, 1 skipped. 빈 값·수치·시간 간격·RGB 불일치·반복 render reference·파일 변조·기존 저장본 보호와 새 CLI 라우팅을 검사했습니다. 건너뛴 항목은 xacro 미설치에 따른 URDF 재생성 검사입니다.
- 교재는 실제 GUI 5장과 실제 변환 터미널 1장을 사용합니다. 원본 PNG·빨간 표시·노션 ZIP으로 제공합니다.
- 전체 교재 상대 링크 81개, 실제 원본과 SVG 이미지 39장, 6개 ZIP의 내부 링크·무결성 검사를 통과했습니다.
- 물리 재생·학습·정책 실행은 이 장의 검증 범위가 아닙니다. 원본 시연은 수집 경로를 검증하는 짧은 예제이며 집기 학습 데이터로 평가하지 않았습니다.
- 실물 리더 USB는 열지 않았습니다. `teleop --record`는 같은 기록 모듈을 사용하지만 실물 리더 수집 검증은 별도입니다.
- 카메라 장착은 calibrated=false입니다. 손목 가림은 실제 TF 보정 전에 해결되지 않았으며 manifest와 교재에 명시했습니다.

```bash
./lekiwi record
./lekiwi export-dataset --input /data/recordings/lekiwi.XXXXXXXX \
  --output /data/datasets/my_new_dataset --repo-id local/my_dataset
```

### 6편 수집 시간 설정 추가

- Max seconds 입력으로 에피소드별 최대 시간을 지정합니다. 기본 30초이며 0은 수동 종료입니다. 기록 중에는 값을 고정하고 원본 manifest에 보관합니다.
- 실제 GUI에서 120초 설정 → 13프레임 수동 종료·저장, 1초 설정 → 정확히 30프레임 자동 종료, 0 설정 → 11프레임 수동 종료·버리기를 확인했습니다. 이전 저장본은 유지됐습니다.
- 관련 검사 60 passed, 1 skipped. 시간 경계와 30초 초과, 무제한 및 입력 잠금 검사를 추가했습니다.
- 실제 GUI 원본 5장과 빨간 표시, 교재·기록지·노션 ZIP을 갱신했습니다. 변환 터미널 캡처는 앞선 별도 검증 실행 결과를 유지했습니다.

## 1~6편 전체 재점검 · 2026-09-08

- 완료 목표·실습 명령·단위·저장 위치·기록지와 구현을 대조했습니다. 3·5편 및 카메라·코스 안내에 남은 녹화 미구현 문구를 6편 수집·변환 안내로 갱신했습니다.
- 1편 90~150분부터 6편까지 시간을 합산했습니다. 실물 없는 기본 과정 375~555분, 4·6편 리더 선택 실습 포함 465~705분입니다. 설치 완료 PC의 계획용 추정이며 실제 수업 측정값이 아닙니다.
- 루트·교육 목차 README에 2일 12~14시간 운영안, 설치·휴식·리더 공유·긴 기록의 실제 대기 시간을 구분했습니다.
- 전체 자동 검사 225 passed, 1 skipped. 도움말 수정 후 배포 관련 검사 33 passed, 1 skipped도 통과했습니다. 생략 항목은 호스트 xacro 미설치에 따른 URDF 재생성 검사입니다.
- 교육자료 상대 링크 84개, 루트·연결 문서 상대 링크 25개, 실제 캡처 원본·SVG 39장과 6개 ZIP의 내부 링크·무결성 검사를 통과했습니다. 변경한 1·3·4·5·6편 ZIP을 재생성했습니다.
- NVIDIA 5.1 요구사항, LeRobot v3의 finalize 안내, Notion ZIP·HTML 가져오기 공식 안내를 다시 확인했습니다. 기존 SOURCES 링크와 설치 사양을 대조하고 ZIP 메뉴의 현재 이름을 반영했습니다.
- 이번 재점검은 문서·코드 대조와 자동 검사입니다. 앞선 GUI·PhysX·데이터 변환 실측 기록을 보존하며 전체 GUI 수업을 다시 진행했다고 간주하지 않습니다. 실물 리더 수업, 실측 TF 보정, Notion 계정 가져오기와 모델 학습은 별도 검증입니다.
