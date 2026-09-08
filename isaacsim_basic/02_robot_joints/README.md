# 2편 · 로봇 구조와 관절 움직이기

**목표:** 링크와 관절을 구분하고, 회전축·회전 중심·각도 제한·구동값이 움직임에 미치는 영향을 확인합니다.
Isaac Sim 5.1.0 Docker 기준, 예상 60~90분입니다. 1편의 Rigid Body/Collider를 먼저 실습하세요.
이 편은 USB나 실제 팔 없이 진행합니다.

이 편의 단일 관절 장면에는 LeKiwi 장착 카메라가 없습니다. 이후 로봇 실행에서는 도면을 반영한 공통 카메라 TF를 사용합니다.
[1~6편의 카메라 적용 범위](../README.md#1~6편의-카메라-설정-적용-범위)를 참고하세요.

## 1. 시작과 준비

저장소 최상위 터미널에서 실행합니다. 첫 설치는 [전체 안내](../README.md)를 따르세요.
기존 Isaac Sim 창을 닫고 프로세스가 종료된 다음 실행합니다.

```bash
export LEKIWI_DOCKER_SUDO=1  # Docker에 sudo가 필요한 PC에서만
export ACCEPT_EULA=Y       # NVIDIA 라이선스를 읽고 동의한 경우
./lekiwi setup sim
./lekiwi basic --lesson joints
```

파란 받침과 주황 막대가 보이고 **Stop 상태**로 시작합니다.
새 작업 파일 경로가 터미널의 `ISAACSIM_BASIC ready` 줄에 출력됩니다.
이번 실습은 복잡한 로봇을 이해하기 위한 **한 관절 교육 모형**입니다. SO101의 질량이나 모터 사양을 재현한 모형은 아닙니다.

## 2. 링크·관절·Articulation 이해하기

| 이름 | 의미 | 이 실습에서 확인할 객체 |
|---|---|---|
| 링크(Link) | 하나의 단단한 몸체 | `Base`, `Arm`: Rigid Body |
| 형상(Shape) | 눈에 보이고 충돌하는 표면 | 각 링크 아래 `Shape`: Collider |
| 고정 관절(Fixed Joint) | 두 기준 사이 이동·회전 고정 | `FixedBase`: 월드에 받침 고정 |
| 회전 관절(Revolute Joint) | 지정 축 주위 회전 하나 허용 | `Shoulder`: Y축 회전 |
| Articulation | 연결된 관절·링크를 로봇 계통으로 계산 | `FixedBase`의 Articulation Root |
| Drive | 목표 각도나 속도를 따라가게 하는 구동 설정 | `Shoulder`의 Angular Drive |

Stage에서 `World > Hinge`를 펼칩니다. `Base`, `Arm`, `FixedBase`, `Shoulder`를 번갈아 선택합니다.
`Base`와 `Arm` 아래의 `Shape`도 펼쳐 보세요. **Stage의 부모·자식 관계만으로 관절이 생기지는 않습니다.**
물리적인 연결은 관절의 `Body 0`, `Body 1`이 가리키는 강체로 결정됩니다.

![교육용 관절 모형과 Stage 구조](images/01-structure.png)

이 모형은 링크 Xform의 Scale을 1로 유지하고 Shape에만 크기를 지정합니다.
그러면 관절의 로컬 위치를 m 단위로 바로 읽을 수 있습니다. 강체를 중첩하여 부모와 자식에
Rigid Body를 중복 추가하지 마세요. 1편의 복합 Collider 구조를 떠올리면 됩니다.

## 3. 회전축과 회전 중심 확인하기

1. Stop 상태에서 Stage의 `Shoulder`를 선택합니다.
2. Property의 검색어를 지우고 `Physics`의 Joint/Revolute Joint 항목을 펼칩니다.
3. 다음 값을 확인합니다. 긴 경로는 필드를 넓히거나 마우스를 올려 전체 경로를 읽습니다.

| 설정 | 값 | 해석 |
|---|---|---|
| Body 0 | `/World/Hinge/Base` | 연결의 첫 강체 |
| Body 1 | `/World/Hinge/Arm` | 연결의 두 번째 강체 |
| Axis | Y | 관절 좌표계 Y축으로 회전 |
| Local Position 0 | (0, 0, 0.15) m | 받침 중심에서 위로 15 cm |
| Local Position 1 | (0, 0, -0.15) m | 막대 중심에서 아래로 15 cm |
| Lower / Upper Limit | -60° / +60° | 허용 회전 범위 |

받침 중심은 월드 Z=0.15 m, 막대 중심은 Z=0.45 m입니다.
따라서 두 앵커의 월드 높이는 `0.15+0.15 = 0.45-0.15 = 0.30 m`로 일치합니다.
이것이 회전 중심입니다. 앵커가 서로 다른 곳에 있으면 Play 순간 물체가 튀거나 강제로 끌려갈 수 있습니다.

![Body 관계와 회전축·제한 속성](images/02-joint.png)

축의 이름은 월드 축과 항상 같지 않습니다. 링크 자세와 Local Rotation이 바뀌면
관절 축도 달라집니다. 이 모형은 초기 회전과 관절 로컬 회전이 모두 0이라 Y축을 쉽게 관찰할 수 있습니다.

## 4. 목표 각도를 바꾸어 움직이기

1. `Shoulder`를 선택한 채 Property 검색창에 `target`을 입력합니다.
2. `Angular Drive`의 `Target Position` 숫자 칸을 **Ctrl+클릭**하여 편집 모드로 전환한 다음 **30**을 입력하고 Enter를 누릅니다.
3. 왼쪽 **Play**를 누릅니다. 주황 막대가 +X 방향으로 기울어지는지 봅니다.
4. **Pause**를 눌러 최종 모습을 관찰합니다. Stop은 초기 배치로 돌아가므로 결과 관찰 때 구분하세요.
5. Stop 후 목표를 **-30**으로 바꾸고 다시 Play 합니다. 반대 방향으로 기울어집니다.
6. Stop 후 목표를 **0**으로 되돌립니다.

![Angular Drive의 목표 각도 입력](images/03-drive.png)

![30도 목표로 실제 물리 시뮬레이션한 결과](images/04-result.png)

GUI/USD의 회전 Drive 목표각은 **degree(도)**입니다.
Isaac Sim의 Python `ArticulationAction(joint_positions=...)`은 **radian(라디안)**입니다.
예를 들어 30°는 약 0.5236 rad입니다. 같은 숫자 30을 그대로 Python 명령으로 보내면 다른 뜻이 됩니다.
[공식 Articulation Controller 설명](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/robot_simulation/articulation_controller.html)

이 실습은 USD Drive만 목표를 정합니다. LeKiwi 실행 프로그램처럼 매 프레임 Python이 목표를 보내는 장면에서는
GUI에 입력한 값이 다음 프레임에 덮어써질 수 있습니다. 어떤 경로가 목표를 정하는지 먼저 확인하세요.

## 5. 관절 제한과 구동 강도 비교

**한 번에 값 하나만 바꾸고, Stop 상태에서 수정한 뒤 Play**합니다.
Property 검색어를 지우고 아래로 스크롤해 `Drive > Angular` 전체 항목을 펼칩니다. 먼저 아래 기본값을 기록합니다.

| 항목 | 교육 모형 기본값 | 역할 |
|---|---:|---|
| Target Position | 0° | 가려는 각도 |
| Target Velocity | 0°/s | 목표 각속도 |
| Stiffness | 1000 | 목표에서 벗어났을 때 되돌리는 정도 |
| Damping | 50 | 목표 속도와 차이가 날 때 움직임을 줄이는 정도 |
| Max Force | 100 | 이 force형 회전 Drive의 최대 토크 한도 |
| Type | force | 힘/토크 기반 구동 |

![제한각과 구동 강도 설정 전체](images/05-gains.png)

수치는 교육용입니다. 다른 로봇의 질량·관성에 그대로 적용하지 않습니다.
설정값의 크기만으로 실제 모터 성능이나 안정성을 보장할 수 없습니다.

### A. 범위 제한

Target Position을 80°로 설정하고 Play 합니다. Upper Limit이 60°이므로 실제 관절은
약 60°에서 제한됩니다. **목표값과 실제값은 다를 수 있습니다.**
GUI Transform은 로컬 위치/회전 표현이고, Drive Target은 명령이므로 같은 종류의 값이 아닙니다.
검사 프로그램은 막대 중심 위치로 실제 각도를 계산합니다.

### B. 목표 유지

기본값에서 목표 30°를 확인한 뒤 Stop 합니다. Stiffness만 10으로 낮춰 Play 합니다.
같은 시간 동안 목표에 얼마나 접근하고 유지하는지 비교합니다. 중력에 의한 오차가 달라질 수 있습니다.
다음 비교 전 Stiffness를 1000으로 복구합니다.

### C. 흔들림

Damping을 50에서 1로 낮춰 같은 목표를 비교합니다. 흔들림이 커지면 Pause/Stop하고 50으로 복구합니다.
화면 프레임 수로 정확한 물리 시간을 추정하지 마세요. PC 성능에 따라 재생 속도가 달라질 수 있습니다.

## 6. LeKiwi와 SO101에 적용해 읽기

관절 모형을 저장하고 Isaac Sim을 닫습니다. 다음 명령으로 번들 로봇을 봅니다.

```bash
./lekiwi sim
```

이 명령은 베이스 키보드 조작을 켜고 팔을 기본 자세로 유지합니다.
**리더암 입력은 연결되지 않으므로 R을 눌러도 팔 추종이 시작되지 않습니다.** 4편에서 구분합니다.
Stage에서 `LeKiwi`를 펼쳐 각 링크와 관절을 찾아보세요. 검색창으로 이름을 찾을 수도 있습니다.

| SO101 관절 순서 | 읽을 이름 | 기본 명령각 |
|---:|---|---:|
| 1 | shoulder_pan | 0° |
| 2 | shoulder_lift | 0° |
| 3 | elbow_flex | 0° |
| 4 | wrist_flex | 0° |
| 5 | wrist_roll | -90° |
| 6 | gripper | 0° |

이 기본 자세는 프로젝트의 시뮬레이터 설정입니다. 리더 모터 보정 결과와 같은 개념이 아닙니다.
바퀴 관절 3개, 수동 롤러 관절 36개, 팔 관절 6개가 있으며 모든 관절에 같은 제어 방식을 적용하지 않습니다.
받침이 고정된 교육 모형과 달리 LeKiwi의 베이스는 바퀴 접촉으로 움직입니다.
전체 로봇 Xform을 드래그하는 것은 바퀴 구동 실습을 대신하지 않습니다.

## 7. 움직이지 않거나 튈 때

| 증상 | 먼저 확인 | 다음 행동 |
|---|---|---|
| 전혀 움직이지 않음 | Play 여부, 선택한 객체가 Shoulder인지 | Drive 목표·Stiffness·Max Force 확인 |
| Shape만 돌아감 | Transform을 바꾼 것은 아닌지 | Stop 후 링크·관절 관계 확인 |
| 시작 순간 튐 | 두 로컬 앵커의 월드 위치 | 같은 회전 중심으로 맞춤 |
| 80°에 도달하지 않음 | Upper Limit=60° | 제한이 적용되는 정상 결과 |
| LeKiwi GUI 값이 유지되지 않음 | Python이 매 프레임 목표를 쓰는지 | 관절 실습 장면에서 Drive를 수정 |
| 로봇 전체가 떨어짐 | 고정식인지 이동식인지, 바닥 Collider | 의도한 모델 구조부터 확인 |

## 8. 저장·과제·검증

`File > Save As`로 `/data/isaacsim_basic/` 아래 새 과제 파일을 저장합니다.
Stop 상태에서 저장하고 `File > Open`으로 다시 열어 값이 유지되는지 확인합니다.
상대 참조가 있는 로봇 자산은 USD 한 파일만 옮기면 누락될 수 있으므로 번들 원본은 이동하지 않습니다.

과제: 목표 30°, -30°, 80°의 결과를 각각 캡처하고 **회전축 / 실제 도달 범위 / 고정되는 링크**를 설명하세요.
[기록지](worksheet.md)에 목표와 관찰값, 실패 원인을 남깁니다.

Isaac Sim 창을 닫은 뒤 검증합니다.

```bash
./lekiwi test-basic  # 객체 물리 + 한 관절 양방향 추종·60도 제한
./lekiwi test-arm    # USB 없이 가상 입력으로 SO101 6개 관절 추종 검사
```

[출처와 검증 범위](SOURCES.md) · [다음: 3편 카메라](../03_robot_cameras/README.md)
