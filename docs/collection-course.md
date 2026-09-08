# 2단계: 모바일 매니퓰레이션 코스

모든 환경 자산은 코드에서 기본 도형으로 생성한다. 별도 USD/URDF/mesh 다운로드,
ROS, Conda 없이 기존 Isaac Docker 이미지로 실행한다. 물체 위치 단위는 m,
회전은 degree이며, 시작 로봇의 +X가 진행 방향, +Y가 왼쪽, +Z가 위쪽이다.

## 실행

이미지를 갱신한 뒤 코스를 연다. Docker에 sudo가 필요하면 각 명령 앞에
`LEKIWI_DOCKER_SUDO=1`을 붙인다. 기존 시뮬레이터는 먼저 종료한다.

```bash
./lekiwi setup sim
ACCEPT_EULA=Y ./lekiwi scene
```

기본 구성은 바깥 원형 도로와 중앙에서 연결되는 십자 도로다. LeKiwi는 중앙에서
시작한다. 원형 도로의 중심 반지름은 2.2 m, 도로 폭은 0.9 m다. 바구니는 중앙에서
3.05 m 떨어진 각 십자 길 끝에 있어 원형 도로를 막지 않는다.
각 길의 중앙에는 약 0.5 m의 물체 없는 주행 공간을 둔다.
도로·차선은 공통 평면 바닥 위의 시각 표시이며 바퀴가 걸리는 추가 충돌은 없다.

| 초기 전체 화면 방향 | 코스 좌표 | 블록·바구니 색 |
|---|---|---|
| 위 | +X | 빨강 red |
| 아래 | -X | 주황 orange |
| 왼쪽 | +Y | 노랑 yellow |
| 오른쪽 | -Y | 초록 green |

**각 길의 색, 블록 수(1개씩 총 4개), 바구니 위치는 고정**이다.
seed가 바뀌면 해당 길 안에서 블록의 XY 위치와 Z축 회전(-180°~180°)이 달라진다. 카메라를 돌리더라도
색상과 길의 대응 관계는 바뀌지 않는다.
블록은 한 변 4 cm·질량 35 g의 동적 물체다. 바구니는 44 x 44 x 18 cm이며,
바닥과 네 벽에 각각 충돌을 적용해 윗부분을 실제로 열어 놓았다.
이는 첫 작업 환경이며 실제 집기 가능 범위·작업 성공률은 teleop으로 확인해야 한다.

`WASD/QE`, 속도 `1/2/3`, `Space`, 카메라 추적 `T`는 기존과 같다.
`scene`은 USB를 열지 않고 팔을 기본 자세로 유지한다. 첫 화면은 코스 전체를 보여준다.

```bash
# 매 실행 블록 위치와 회전을 랜덤하게: seed를 생략한다.
ACCEPT_EULA=Y ./lekiwi scene
# 작업 지정: 초록 블록을 빨강 바구니에 넣기
ACCEPT_EULA=Y ./lekiwi scene --seed 42 --block green --basket red
```

위치는 중앙 주행 공간·시작 로봇·다른 물체와 겹치지 않도록 제한한다.
랜덤 seed와 **초기 위치·회전·색상·바구니 ID·선택한 작업**은
매번 새 `data/scenes/course.XXXXXXXX/layout.json`에 저장한다.
함께 저장되는 `course.usda`는 외부 참조 없는 환경 파일이며 Isaac에서 불러올 수 있다.
이 USD는 환경만 포함하며 로봇은 기존 번들에서 따로 불러온다.
저장되는 것은 초기 배치이지 조작 후 위치나 데이터셋 프레임 기록이 아니다.

## 랜덤 배치로 teleop

`Collection Task` 선택 창은 표시하지 않는다. 모든 색 블록 4개가 함께 생성되며,
사용자가 직접 주행하고 원하는 블록을 집는다. 아래 명령은 매 실행마다 네 블록의
위치와 바닥 위 회전 방향을 새로 생성한다. 길의 모양·길별 색·바구니 위치는 고정이다.

```bash
ACCEPT_EULA=Y ./lekiwi teleop \
  --port /dev/serial/by-id/본인_리더_장치 --id so101_leader --scene random
```

실행 중인 물체를 갑자기 옮기지는 않는다. 새로운 배치는 재실행 시 적용한다.
기존 CLI의 `--block`/`--basket`과 저장 파일의 작업 정보는 호환용으로 유지하지만,
현재 teleop에서는 자동 동작이나 작업 완료 판정에 사용하지 않는다.

이전 직선 코스(version 1)의 저장 파일도 계속 재생할 수 있다.
`--start-count 3 --middle-count 5`처럼 개수를 지정하면 이전 직선 코스를 만든다.
색상 태스크는 새 원형+십자 코스(version 2)에서만 지원한다.

## 같은 환경 다시 사용

출력 로그의 `LEKIWI_COURSE saved=/data/scenes/course.XXXXXXXX` 경로를 사용한다.
CLI에 넘기는 경로는 호스트 경로가 아니라 Docker 안의 `/data/...` 경로다.

```bash
ACCEPT_EULA=Y ./lekiwi scene --layout /data/scenes/course.XXXXXXXX/layout.json

ACCEPT_EULA=Y ./lekiwi teleop \
  --port /dev/serial/by-id/본인_리더_장치 --id so101_leader \
  --scene /data/scenes/course.XXXXXXXX/layout.json
```

같은 저장 배치로 새 실행을 만들며 이전 파일을 덮어쓰지 않는다.
통합 teleop에서는 기존 보정 재사용 질문과 `R` 활성화 절차가 유지된다.
향후 데이터셋 수집도 이 `layout.json`을 에피소드 환경 설정으로 사용한다.
아직 카메라 동기화·LeRobotDataset 기록·런타임 에피소드 리셋·바구니 성공 판정은 없다.

## Isaac Script Editor에 붙여넣기

Isaac Sim 5.1의 Z-up, metre-scale stage에서 실행한다. 기존 stage를 지우지 않으며
코스가 이미 있으면 중복 생성을 거부한다. 기존 바닥이 있으면 겹칠 수 있으므로
빈 stage 사용을 권장한다. SimulationApp을 새로 만들거나 재생을 자동 시작하지 않는다.

```python
import sys
sys.path.insert(0, "/opt/lekiwi/isaac_sim")
from collection_course import add_in_script_editor
saved = add_in_script_editor(seed=42, block="green", basket="red")
```

Docker 밖의 Isaac에서는 `/opt/lekiwi/isaac_sim` 대신 clone한 프로젝트의
`isaac_sim` 절대 경로를 쓰고, `output_dir="/쓰기가능한/폴더"`를 지정한다.
이 경로는 코스만 추가하며 기존 로봇·teleop을 교체하지 않는다.

## 검증

```bash
ACCEPT_EULA=Y ./lekiwi test-scene
```

USB 없이 로봇 시작 위치, 블록의 바닥 안착, 바구니로 떨어뜨린 시험 블록의
안착 위치를 확인한다. 실제 팔로 블록을 집어 넣는 작업 검증을 대신하지 않는다.
