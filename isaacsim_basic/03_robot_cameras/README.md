# 3편 · 코드로 카메라를 만들고 LeKiwi 좌표 이해하기

먼저 카메라 생성·화각·자세를 작은 예제로 확인한 뒤 실제 LeKiwi 전방·손목 카메라에 연결합니다.

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


## 1. 카메라 생성

[01_camera.py](experiments/01_camera.py)

```bash
./lekiwi basic --chapter 3
```

```python
camera = UsdGeom.Camera.Define(stage, "/World/Camera")
camera.CreateFocalLengthAttr(24)
# camera.CreateFocalLengthAttr(48)
camera.CreateHorizontalApertureAttr(20.955)
camera.CreateClippingRangeAttr(Gf.Vec2f(.01, 100))
```

기본 Viewport는 Perspective입니다. Viewport 위쪽 카메라 선택 메뉴에서 `/World/Camera`를 선택합니다.
Stage에서 Camera를 선택해 Property의 Camera·Transform 항목을 코드와 비교합니다.

![기본 카메라와 속성](images/08-code-first.png)

## 2. 같은 자리에서 화각 바꾸기

24 줄을 주석 처리하고 48 줄을 해제합니다. 창을 닫고 같은 명령으로 재실행한 뒤 Camera를 다시 선택합니다.
카메라 위치는 유지되지만 화면에 보이는 범위는 좁아지고 객체는 크게 보입니다.
`FocalLength`와 `HorizontalAperture`의 비율이 화각을 결정합니다. 둘은 USD에서 같은 렌즈 단위를 사용합니다.
**해상도는 픽셀 개수**, 화각은 보이는 각도, Clipping은 표시하는 거리 범위입니다. 서로 구분합니다.

## 3. 위치와 방향

```python
pose = Gf.Matrix4d().SetLookAt(eye, target, up).GetInverse()
camera.AddTransformOp().Set(pose)
```

파일의 eye는 카메라 위치, target은 바라볼 점, up은 월드의 위쪽입니다.
`SetLookAt`의 역행렬을 카메라의 월드 자세로 씁니다. eye의 X만 바꾸고 같은 target을 바라보게 하면 시선도 함께 회전합니다.
USD 카메라는 **-Z가 렌즈 정면, +Y가 위**입니다. ROS optical의 +Z 정면, +Y 아래와 다릅니다.
렌즈 중심을 맞춰도 축 방향이 잘못되면 전혀 다른 곳을 봅니다.

## 4. LeKiwi로 확장

기존 창을 닫고 다음을 실행합니다. USB 리더는 필요 없습니다.

```bash
./lekiwi scene
```

좌측 Perspective, 우측 Front Camera가 기본입니다. 좌측 Viewport를 클릭하고 **C**로 전체 → front → wrist를 전환합니다.
**T**는 추적 시점, **P**는 Viewport 이미지 저장, **F8**은 로봇 초기화와 라인 안 큐브 재배치입니다.
이 단축키들은 프로젝트 코드이며 Isaac Sim 기본 기능은 아닙니다. 카메라 선택 메뉴로 같은 시점에 접근할 수도 있습니다.

## 5. 렌즈 좌표축과 부모 링크

| 기준 | 오른쪽/위/정면 규약 | 주의점 |
|---|---|---|
| optical frame | +X 오른쪽, +Y 아래, +Z 촬영 정면 | 설정 JSON이 사용하는 규약 |
| USD Camera | +X 오른쪽, +Y 위, -Z 촬영 정면 | 자식 Camera에 X축 180° 변환 적용 |
| 로봇 base_link | +X 전방, +Y 왼쪽, +Z 위 | 카메라의 정면축과 구분 |

**렌즈 중심은 optical frame의 원점**입니다. 외형 상자의 가운데를 원점으로 맞추면 렌즈가 어긋날 수 있습니다.
JSON에는 optical 기준 quaternion을 넣습니다. 자식 Camera의 X축 180° 변환을 다시 곱해 넣지 않습니다.

| 카메라 | 물리 부모 | 부모 기준 렌즈 중심 (m) |
|---|---|---|
| front | base_link | (0.106898279335, 0.001703025019, -0.006396) |
| wrist | wrist_link | (-0.058779995352, -0.113835885897, 0.018277254719) |

손목 카메라는 현재 **wrist_roll 이전 링크**에 달려 있습니다.
실제 카메라가 집게 회전과 함께 돌아가는 구조라면 `gripper_link`를 부모로 지정하고 변환을 다시 구해야 합니다.
이 편은 기본 자세에서 영상을 확인합니다. 여러 팔 자세에서의 실제 영상 가림 검사는
4편에서 사용자가 리더 조작을 준비한 뒤 이어서 수행합니다.

## 6. 도면의 soarm base 기준 TF를 반영하기

TF는 여기서 **두 좌표계 사이의 위치와 회전 관계**를 뜻합니다. ROS 설치 자체가 필수인 것은 아닙니다.
이번 기본값의 입력 치수와 도면 재현 자세는 다음과 같습니다.

| 카메라 | SOARM base 기준 렌즈 중심 (mm) | 촬영 정면 해석 |
|---|---|---|
| front | (86.91, 0, -59.28) | +X 전방 |
| wrist | (205.40, 0, 208.58) | 전방 아래 45° |

재현 자세(deg): `shoulder_pan=0, shoulder_lift=-90, elbow_flex=90, wrist_flex=0, wrist_roll=-90, gripper=0`.
이 자세는 도면을 보고 맞춘 관절각이며 실물 관절각 측정값은 아닙니다. 기본 실행 자세와도 다릅니다.
손목의 SOARM base 기준 값은 **이 자세에서만** 위 표와 일치하고, 다른 자세에서는 팔을 따라 변합니다.
`mounts.json`의 `measurement`에는 입력 치수·재현 자세·가정을 남겼습니다.
Y·정면·실제 고정 링크·측정 자세를 더 정확히 확인하면 같은 환산식으로 갱신합니다.

실측 때 아래 정보를 함께 남깁니다.

- 기준: `soarm_base_link`, 카메라의 렌즈 중심과 촬영 정면.
- translation 길이 단위: m 또는 mm를 명시.
- quaternion 순서: 이 프로젝트는 **x, y, z, w**.
- 좌표축 규약: optical인지 다른 규약인지 명시.
- 손목 카메라를 측정한 **동일 시점의 6개 관절각**과 단위.
- 카메라가 실제로 고정된 링크.

S=soarm base, L=부착 링크, C=optical frame이라 할 때:

```text
T_L_C = inverse(T_S_L(q)) × T_S_C
```

`T_A_B`는 B 좌표를 A 좌표로 바꾸는 변환입니다. q는 측정 당시 팔 자세입니다.
손목 카메라의 측정값을 soarm base에 그대로 고정하면 팔을 움직여도 카메라가 따라가지 않습니다.
측정 자세에서 **부착 링크 기준으로 환산**해야 합니다.

front의 예로, 현재 URDF의 `base_link → soarm_base_link`는
(0.019988279335, 0.001703025019, 0.052884) m이고 회전은 0입니다.
같은 축 방향으로 표현한 점이라면 base 기준 위치는 이 이동값과 soarm base 기준 위치를 더해 구합니다.
손목에는 관절 회전이 포함되므로 같은 단순 덧셈을 적용하면 안 됩니다.

### 설정 파일의 작업 복사본 만들기

저장소 최상위에서 실행합니다. 기존 파일을 덮어쓰지 않는 명령입니다.

```bash
mkdir -p data/cameras
cp -n isaac_sim/assets/cameras/mounts.json data/cameras/mounts.json
```

호스트 `data/cameras/mounts.json`을 편집합니다.
이 파일은 컨테이너에서 `/data/cameras/mounts.json`으로 보입니다.
측정하지 않은 상태에서는 `calibrated: false`를 유지합니다.

```bash
LEKIWI_CAMERA_CONFIG=/data/cameras/mounts.json LEKIWI_COURSE_LAYOUT=random ./lekiwi sim
```

기존 Isaac Sim을 종료한 뒤 실행해야 합니다. JSON의 quaternion 길이는 1이어야 하며,
허용 범위와 숫자 형식이 잘못되면 로더가 오류를 냅니다. 이것만으로 실측 보정 정확성이 보장되지는 않습니다.
이번 과정에서 TF 실측값을 임의로 만들거나 원본 장착값을 보정 완료로 표시하지 않습니다.


## 완료 기준

[기록지](worksheet.md)에 24/48 렌즈의 화면 차이, front/wrist의 부모 링크, 기준 프레임과 렌즈 정면을 적습니다.
보정 값을 수정할 때 mm → m 변환과 회전 단위를 확인합니다. 렌즈가 링크 안에 들어가면 화면이 로봇 몸체에 가려질 수 있습니다.
3편은 영상·좌표를 이해하는 실습이며 두 카메라 동기 기록은 6편에서 진행합니다.

[공식 자료](SOURCES.md) · [다음: 4편](../04_teleoperation/README.md)
