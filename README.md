# lekiwi_isaacsim

Isaac Sim 에서 **LeKiwi 4대를 한 사람이 번갈아 텔레옵**하는 환경이다. 3.0 × 2.0 m 경기장,
가운데 네트, 진영별 바구니, 공 16개가 들어 있고, 키보드 하나로 베이스를, SO-101 Leader 팔
하나로 선택된 로봇의 팔을 조종한다.

## 무엇이 들어 있나

```
run_teleop.sh                 텔레옵 실행 (스테이지 경로 자동)
run_leader_sender.sh          Leader 팔 → ZMQ 송신 (텔레옵 전에 먼저 띄운다)
scripts/                      텔레옵 본체와 의존 모듈
arena/                        경기장 USD 생성·검증 스크립트
stages/                       최종 경기장 USD (4층 서브레이어)
assets/                       LeKiwi + SO-101 로봇 USD
```

## 요구 환경

| | |
|---|---|
| Isaac Sim | 6.0.1 (conda 환경 `isaacsim-6.0.1`, Python 3.12) |
| Leader 팔 | LeRobot 환경 (conda `lerobot_so102_b601`), SO-101 Leader, 12 V |
| OS | Ubuntu 24.04 에서 개발·검증 |

환경 이름이 다르면 `ISAACSIM_ENV` / `LEROBOT_ENV` 로 넘긴다. Isaac Sim 과 ROS 의
`PYTHONPATH` / `LD_LIBRARY_PATH` 가 섞이면 깨지므로, 실행 스크립트가 그 변수들을 벗겨낸 뒤
conda 환경으로 넘긴다. 직접 `python` 을 부를 때도 같은 방식을 따라야 한다.

## 실행

터미널 1 — Leader 팔 송신:

```bash
./run_leader_sender.sh /dev/ttyACM1
```

터미널 2 — 텔레옵:

```bash
./run_teleop.sh
```

Leader 팔 없이 베이스만 움직여 볼 수도 있다. 그때는 터미널 2만 띄우면 된다.

### 조작

| 키 | 동작 |
|---|---|
| `T` / `F` | 다음 / 이전 로봇 (Blue 1 → Blue 2 → Red 1 → Red 2 순환) |
| `W` `S` | 전진 / 후진 |
| `A` `D` | 좌 / 우 평행 이동 |
| `Z` `X` | 좌 / 우 회전 |
| `Q` | 정지 |
| `[` `]` | 속도 감소 / 증가 |
| `Esc` | 종료 |

Isaac Sim 창에 포커스가 있어야 키가 먹는다. 선택되지 않은 3대의 베이스에는 매 프레임 0 이
나가고, 로봇을 바꾸면 눌려 있던 이동키가 초기화되며 직전 로봇은 즉시 멈춘다. Leader 스트림이
0.5 초 넘게 끊기면 팔은 마지막 목표 자세를 유지한다 (`--leader-timeout`).

주요 옵션: `--fps 60`, `--linear-speed 0.35`, `--rotation-speed 75`, `--headless`,
`--run-seconds N`, `--low-render`.

## 경기장

내부 3.0 × 2.0 m, Z-up, 중심 (0, 0, 0), 물리 120 Hz. 모든 prim 은 `/World/Arena` 아래에 있다.

- **네트**: X = 0, 높이 0.30 m. 아래 0.07 m 는 공이 통과하지 못하는 벽이고, 양 끝에 12 × 10 × 13 cm 고정대가 벽에 붙어 있다.
- **바구니**: 진영마다 하나. 외곽 12 × 26 cm, 벽·테두리 두께 12 mm. TeamRed 는 회색, TeamBlue 는 황토색.
- **공**: 지름 70 mm 로 보이는 구 16개 (빨강 10 · 노랑 4 · 파랑 2). 보이는 구에는 콜라이더가 없고, 안쪽의 **정육면체**가 충돌을 담당한다 — 평평한 턱이 점이 아니라 면으로 물리게 하려는 것이다 (한 변 60 mm).
- **로봇**: 4대, Red 는 X < 0, Blue 는 X > 0, 각자 로컬 +X 가 네트를 향한다.

### 다시 만들기

`stages/` 의 USD 는 아래 순서로 재생성할 수 있다. 각 단계는 앞 단계의 결과를 입력으로 받는다.

```bash
python arena/create_net_arena.py      # 경기장만
python arena/add_four_lekiwi.py       # 로봇 4대 삽입
python arena/create_turf_variants.py  # 인조잔디 바닥
python arena/sim_grip_tune.py         # 그리퍼·공 물리 override 레이어
```

`arena/verify_net_arena.py` 는 생성된 스테이지를 물리까지 돌려 검사한다. **지금 이 검증기는
일부 기대값이 옛 사양(흰 공, 34 cm 바구니)에 머물러 있어 그 항목들이 FAIL 로 뜬다** — 통과
여부가 아니라 개별 항목을 읽어야 한다.

## 알려진 한계

- `stages/` 의 최종 USD 는 네 겹 서브레이어다. `..._grip.usd` 하나만 떼어 가면 열리지 않는다.
- 공의 안정 높이는 보이는 구가 아니라 **안쪽 정육면체의 반높이**가 정한다. 정육면체 크기를
  바꾸면 공이 놓이는 높이도 같이 바뀐다.
- 로봇 베이스는 3륜 홀로노믹이고 시뮬레이션에서 회전이 크게 감쇠돼 있다. 제자리 회전보다
  평행 이동이 훨씬 잘 듣는다.
