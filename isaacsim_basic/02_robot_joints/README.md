# 2편 · 코드로 관절·회전축·Drive 만들기

1장의 강체 두 개를 연결하고 하나의 모터처럼 목표 각도를 추종하게 만듭니다. 실물 장비는 사용하지 않습니다.

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


## 1. 기준 모형 실행

[01_joint_drive.py](experiments/01_joint_drive.py)

```bash
./lekiwi basic --chapter 2
```

`build_scene()`에는 Base·Arm 강체 생성, 바닥에 고정하는 FixedJoint, 두 강체 사이 RevoluteJoint가 들어 있습니다.
먼저 기본 0도 상태를 Play로 확인합니다.

![Stage에서 관절 찾기](images/07-code-first.png)

## 2. 연결 관계 읽기

```python
fixed = UsdPhysics.FixedJoint.Define(stage, "/World/Hinge/FixedBase")
fixed.CreateBody1Rel().SetTargets(["/World/Hinge/Base"])
UsdPhysics.ArticulationRootAPI.Apply(fixed.GetPrim())
joint = UsdPhysics.RevoluteJoint.Define(stage, "/World/Hinge/Shoulder")
joint.CreateBody0Rel().SetTargets(["/World/Hinge/Base"])
joint.CreateBody1Rel().SetTargets(["/World/Hinge/Arm"])
```

FixedJoint의 반대쪽 Body가 비어 있으면 월드에 고정합니다. RevoluteJoint는 Base와 Arm 사이에 하나의 회전 자유도를 만듭니다.
ArticulationRoot는 이 연결을 로봇 관절 계통으로 해석하는 시작점입니다.

`LocalPos0`, `LocalPos1`은 각 Body 기준의 접점 위치입니다. 모형에서는 Base 윗부분과 Arm 아랫부분이 같은 월드 위치에 놓입니다.
모양을 만드는 Scale은 자식 Shape에 적용했습니다. 강체 자체를 확대하면 관절 기준 거리까지 달라져 혼동하기 쉽습니다.

## 3. 회전축과 제한

```python
joint.CreateAxisAttr("Y")
joint.CreateLowerLimitAttr(-60)
joint.CreateUpperLimitAttr(60)
```

이 값들은 **degree**입니다. 축은 해당 관절 프레임 기준입니다.
Stage의 `/World/Hinge/Shoulder`를 선택하여 Property의 Axis와 Lower/Upper Limit을 찾아 코드와 비교합니다.
연결된 두 강체의 자기 충돌은 `CreateCollisionEnabledAttr(False)`로 껐습니다.

## 4. 목표 각도 바꾸기

파일 끝의 기본 줄을 주석 처리하고 +30도 줄을 활성화합니다.

```python
# drive.CreateTargetPositionAttr(0)
drive.CreateTargetPositionAttr(30)
# drive.CreateTargetPositionAttr(-30)
# drive.CreateTargetPositionAttr(80)
```

창을 닫고 재실행 → Play. 같은 방법으로 -30도도 확인합니다.
마지막에는 80도를 명령하여 실제 관절이 상한인 약 60도에서 멈추는지 봅니다.
목표값과 실제 상태가 다를 수 있다는 점이 핵심입니다.

## 5. Stiffness·Damping·Max Force

```python
drive = UsdPhysics.DriveAPI.Apply(joint.GetPrim(), "angular")
drive.CreateTypeAttr("force")
drive.CreateStiffnessAttr(1000)
# drive.CreateStiffnessAttr(20)
drive.CreateDampingAttr(50)
drive.CreateMaxForceAttr(100)
```

Stiffness는 목표 오차에 대한 복원 반응, Damping은 속도에 대한 감쇠, Max Force는 구동 힘/토크 상한입니다.
회전 관절에서는 토크를 생각합니다. 목표 30도를 유지하고 Stiffness만 20으로 바꿔 느린 응답·처짐을 관찰합니다.
다음에는 원래 값으로 복원한 뒤 Damping만 낮춰 흔들림을 비교합니다.

수치가 크다고 무조건 좋은 제어가 아닙니다. 물리 시간 간격·질량·관성도 영향을 줍니다.
처음부터 여러 값을 바꾸면 어느 변화가 원인인지 구분하기 어렵습니다.

## 6. 저장과 다시 시작

동일한 설정으로 다시 보려면 표준 Stop → Play를 사용합니다.
코드 수정은 재실행합니다. GUI에서 바꾼 USD를 남기려면 `File > Save As`에서 `/data/isaacsim_basic/` 아래 새 파일에 저장합니다.
**USD 저장이 Python 소스까지 수정하지는 않습니다.** 제출할 때 변경한 `.py`도 함께 보관합니다.

완료 기준: [기록지](worksheet.md)에 0/+30/-30/80도의 목표·관측 각도와 Stiffness 실험 결과를 남깁니다.

[공식 자료](SOURCES.md) · [다음: 3편](../03_robot_cameras/README.md)
