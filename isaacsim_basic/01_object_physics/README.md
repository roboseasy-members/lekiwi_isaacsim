# 1편 · 코드로 배우는 객체와 물리 성질

목표는 객체를 그리는 것, 힘을 받는 것, 다른 객체와 부딪히는 것을 구분하는 것입니다.
완성된 환경의 버튼을 누르는 대신 `Cube.Define`, `RigidBodyAPI`, `CollisionAPI` 코드를 직접 바꿉니다.

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


## 1. 중력도 충돌도 없는 기본 실행

[학생 파일: 01_no_gravity.py](experiments/01_no_gravity.py)

```bash
./lekiwi basic --chapter 1
```

파일 안 `build_scene(stage)`가 장면을 만듭니다. `main()`은 Isaac Sim을 시작하고 창을 유지합니다.
`SimulationApp`을 만든 **다음**에 `omni`와 `pxr` 모듈을 읽는 순서를 지킵니다.

```python
cube = UsdGeom.Cube.Define(stage, "/World/PracticeCube")
cube.CreateSizeAttr(.1)
cube.AddTranslateOp().Set(Gf.Vec3d(0, 0, .7))
cube.CreateDisplayColorAttr([Gf.Vec3f(.2, .6, .95)])
```

`Define`은 Stage의 경로에 객체를 만듭니다. 한 변은 0.1 m, 중심 높이는 0.7 m입니다.
색상 RGB는 0~1입니다. 이 네 줄만으로는 움직이는 물체가 되지 않습니다.

```python
UsdPhysics.RigidBodyAPI.Apply(cube.GetPrim())
UsdPhysics.MassAPI.Apply(cube.GetPrim()).CreateMassAttr(.1)
body = PhysxSchema.PhysxRigidBodyAPI.Apply(cube.GetPrim())
body.CreateDisableGravityAttr(True)
# body.CreateDisableGravityAttr(False)
# UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
```

동적 강체는 유지하되 `DisableGravity=True`로 중력을 끕니다. Collider 줄은 주석이므로 큐브의 접촉은 없습니다.
Play를 눌러도 큐브는 높이 0.7 m에 머뭅니다. 바닥의 Collider는 이미 켜져 있지만 **큐브에도 Collider가 있어야** 접촉합니다.

![기본 Isaac Sim에서 큐브 확인](images/17-code-first.png)

먼저 주황색 `CreateDisplayColorAttr` 줄의 주석을 해제하고 기본 파란색 줄을 주석 처리합니다.
재실행하여 색상만 달라지는지 확인합니다. 두 줄을 모두 활성화하면 뒤의 값이 앞의 값을 덮어씁니다.

## 2. 중력만 켜기

같은 파일에서 다음과 같이 한 줄씩 교체합니다.

```python
# body.CreateDisableGravityAttr(True)
body.CreateDisableGravityAttr(False)
# UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
```

재실행 → Play. 큐브는 떨어져 바닥을 통과합니다. 화면에서 사라졌다고 삭제된 것은 아닙니다.
Stage의 `/World/PracticeCube`를 선택하고 Property의 높이를 확인한 다음 Stop을 누릅니다.
비교용 정답 파일은 [02_gravity_only.py](experiments/02_gravity_only.py)입니다.

```bash
./lekiwi basic --experiment 2
```

## 3. 접촉까지 켜기

```python
body.CreateDisableGravityAttr(False)
UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
```

다시 실행하면 큐브가 바닥에 멈춥니다. 바닥 윗면이 Z=0이고 큐브 한 변이 0.1 m이므로 중심 높이는 약 **0.05 m**입니다.
정답 파일 [03_gravity_collision.py](experiments/03_gravity_collision.py)은 `./lekiwi basic --experiment 3`으로 실행합니다.

| 조건 | 동적 강체 | 중력 | 큐브 접촉 | 예상 |
|---|---|---|---|---|
| 1 | O | X | X | 공중 유지 |
| 2 | O | O | X | 바닥 통과 |
| 3 | O | O | O | 바닥에 정지 |

바닥은 움직이지 않으므로 `RigidBodyAPI` 없이 `CollisionAPI`만 적용합니다.
큐브와 바닥의 크기·좌표는 m, 질량은 kg, 중력 가속도는 m/s²입니다.

## 4. 질량과 중력 가속도

[04_mass_gravity.py](experiments/04_mass_gravity.py)를 열고 실행합니다.

```bash
./lekiwi basic --experiment 4
```

주황 큐브 0.1 kg, 파랑 큐브 1 kg이 같은 높이에서 출발합니다. 이 예제에는 공기 저항이 없습니다.
질량이 다르다고 무거운 큐브가 더 빨리 자유 낙하하지는 않습니다.

```python
scene.CreateGravityMagnitudeAttr(9.81)
# scene.CreateGravityMagnitudeAttr(1.62)
```

기본 줄 대신 아래 줄을 사용해 달 중력으로 바꾸고 낙하 속도를 비교합니다.
파일 아래 `CubeHeavy` 질량을 5 kg으로 바꾸는 줄도 주석 해제해 봅니다.
**질량을 0으로 만들어 중력을 끄지 않습니다.** USD의 0 질량은 자동 계산 의미가 있으므로 중력의 ON/OFF API와 구분합니다.

## 5. 마찰과 경사면

[05_friction.py](experiments/05_friction.py) → `./lekiwi basic --experiment 5`

두 경사면은 같은 15도이며 큐브의 크기·질량도 같습니다. 마찰계수만 0.05 / 0.8입니다.
`material()` 안의 실제 API를 확인합니다.

```python
physics = UsdPhysics.MaterialAPI.Apply(mat.GetPrim())
physics.CreateStaticFrictionAttr(friction)
physics.CreateDynamicFrictionAttr(friction)
UsdShade.MaterialBindingAPI.Apply(prim).Bind(mat, materialPurpose="physics")
```

정지 마찰은 미끄러지기 시작하는 조건, 동적 마찰은 미끄러지는 동안의 저항입니다.
`materialPurpose="physics"`는 물리 재질을 연결합니다. 화면 색상과는 별개입니다.
같은 재질을 해당 큐브와 경사면 **양쪽**에 적용하여 혼합 규칙이 비교를 흐리지 않게 했습니다.

파일 맨 아래 Low 재질의 두 마찰값을 .8로 바꾸는 세 줄을 주석 해제합니다.
다시 실행하면 두 큐브의 미끄러짐이 비슷해져야 합니다. 한 번에 경사각까지 바꾸지 않습니다.

## 6. 반발계수

[06_restitution.py](experiments/06_restitution.py) → `./lekiwi basic --experiment 6`

공 두 개가 동일한 높이에서 떨어집니다. 공과 받침대의 반발계수는 각 쌍이 0 / 0.8입니다.
아래쪽의 `.CreateRestitutionAttr(.3)` 줄을 해제하여 높은 쪽만 0.3으로 낮춥니다.
반발계수 범위는 0~1이며 접촉 전후 수직 상대 속도에 관련됩니다. **0.8이 원래 높이의 80%로 튄다는 뜻은 아닙니다.**
중력·초기 높이·질량을 유지하고 첫 반동의 높이를 비교합니다.

## 7. 기본 UI와 코드 연결하기

Stage에서 객체 선택 → Property에서 Transform과 Physics 항목을 찾습니다.
직접 만드는 연습은 실행 창을 닫은 뒤 `./lekiwi basic --lesson blank`로 시작합니다.
기본 메뉴 `Create > Mesh > Cube`로 객체를 만든 다음 Property의 `Add > Physics`에서 Rigid Body와 Collider를 추가합니다.
메뉴로 만든 속성과 스크립트가 만든 속성의 이름을 비교합니다. 버전에 따라 메뉴 위치는 달라질 수 있습니다.

바구니 보충 실습은 `./lekiwi basic --lesson basket`입니다. 바닥과 네 벽을 별도 Collider로 만듭니다.
입구가 막힌 단일 Convex Hull로 만들면 큐브가 안에 들어가지 못할 수 있습니다.

## 완료 기준

[실습 기록지](worksheet.md)에 각 조건의 예측·관찰·수정 코드를 남깁니다.
중력만 켠 물체가 바닥을 통과하는 이유, 무거운 물체도 같은 가속도로 떨어지는 이유,
색상 재질과 물리 재질의 차이를 설명하면 다음 장으로 넘어갑니다.

[공식 자료와 촬영 기록](SOURCES.md) · [다음: 2편](../02_robot_joints/README.md)
