# experiments 코드 읽기 · 실행 전에 무엇을 볼까

**먼저 Python 파일 맨 위의 설명을 읽고, 실행할 장면과 바꿀 값을 확인하세요.**
각 파일에는 목적·실행 명령·읽는 순서·예상 결과를 적었습니다.
이 문서는 그 설명에서 사용하는 Python 표현과 수업 전체의 코드 연결을 풀어 설명합니다.

코드 실습은 앞의 마우스 실습을 마친 뒤 진행합니다. 4~6장은 교재의 기존 빨주노초 맵을 사용합니다.
[전체 수업 순서](README.md) · [1장 교재](01_object_physics/README.md) · [6장 교재](06_lekiwi_dataset/README.md)

## 1. 파일 이름과 실행 명령 연결하기

VS Code에서 **Ctrl+P → 아래 파일 경로 입력 → Enter**로 파일을 엽니다.
명령은 같은 노트북의 VS Code 터미널에서, **`ls lekiwi`가 파일을 찾는 저장소 최상위 폴더**에서 실행합니다.
표의 파일 경로 앞에는 `isaacsim_basic/`가 붙습니다.

### 1~3장: 코드를 실행하면 장면이 만들어집니다

| 파일 | 실행 명령 | 처음 확인할 결과 |
|---|---|---|
| [01_object_physics/experiments/00_empty_stage.py](01_object_physics/experiments/00_empty_stage.py) | `./lekiwi basic --script 01_object_physics/experiments/00_empty_stage.py` | 직접 제작할 빈 Stage |
| [01_object_physics/experiments/01_no_gravity.py](01_object_physics/experiments/01_no_gravity.py) | `./lekiwi basic --experiment 1` | Play에서도 공중에 머무는 큐브 |
| [01_object_physics/experiments/02_gravity_only.py](01_object_physics/experiments/02_gravity_only.py) | `./lekiwi basic --experiment 2` | 떨어져 바닥을 통과하는 큐브 |
| [01_object_physics/experiments/03_gravity_collision.py](01_object_physics/experiments/03_gravity_collision.py) | `./lekiwi basic --experiment 3` | 바닥에 멈추는 큐브 |
| [01_object_physics/experiments/04_mass_gravity.py](01_object_physics/experiments/04_mass_gravity.py) | `./lekiwi basic --experiment 4` | 같은 높이의 가벼운 큐브·무거운 큐브 |
| [01_object_physics/experiments/05_friction.py](01_object_physics/experiments/05_friction.py) | `./lekiwi basic --experiment 5` | 마찰이 다른 경사면 두 개와 큐브 |
| [01_object_physics/experiments/06_restitution.py](01_object_physics/experiments/06_restitution.py) | `./lekiwi basic --experiment 6` | 반발계수가 다른 공과 받침대 |
| [02_robot_joints/experiments/01_joint_drive.py](02_robot_joints/experiments/01_joint_drive.py) | `./lekiwi basic --chapter 2` | 고정 받침·회전 팔·목표 각도 |
| [03_robot_cameras/experiments/01_camera.py](03_robot_cameras/experiments/01_camera.py) | `./lekiwi basic --chapter 3` | `/World/Camera` 시점과 렌즈 차이 |

`--chapter 1`은 `--experiment 1`과 같은 **01_no_gravity.py 하나**를 실행합니다.
`--experiment 4`는 **1장의 질량 실험**입니다. 장 번호와 실험 번호를 구분하세요.

예를 들어 01_no_gravity.py에서 중력을 켰다면, 수정 결과도 `--experiment 1`로 확인합니다.
`--experiment 2`를 실행하면 따로 준비된 02_gravity_only.py가 열립니다.
현재 실행한 파일은 터미널의 **`STUDENT_SCRIPT source=...`**에서 확인할 수 있습니다.

### 4·5장: 기존 코스 실행기가 여러 파일을 함께 사용합니다

4장의 주 명령은 `./lekiwi scene` 또는 교재의 실제 USB 경로를 넣은 `./lekiwi teleop ...`입니다.
5장은 같은 teleop 명령에 `--record`를 추가합니다. 전체 명령과 연결 안전 절차는 [4장](04_teleoperation/README.md)·[5장](05_data_recording/README.md)을 따릅니다.

| 읽을 코드 | 실제 역할 |
|---|---|
| [isaac_sim/keyboard_drive.py](../isaac_sim/keyboard_drive.py) | 색상 코스·가상 로봇·베이스 조작을 연결하고 속도 기본값을 정함 |
| [06_lekiwi_dataset/experiments/01_lekiwi_recording.py](06_lekiwi_dataset/experiments/01_lekiwi_recording.py) | 같은 코스에서 영상·상태·명령·저장 상태를 관리함. 파일 위치는 기존 경로 유지 |

아래 둘은 관절 원리를 더 알아보는 **보충 예제**입니다. 본 수업의 코스 텔레옵·시연 취득은 위 명령으로 진행합니다.

| 보충 파일 | 실행 | 확인할 원리 |
|---|---|---|
| [04_teleoperation/experiments/01_joint_input.py](04_teleoperation/experiments/01_joint_input.py) | `./lekiwi basic --chapter 4` | J/L/K 입력 → 단일 관절 목표 → 실제 움직임 |
| [05_data_recording/experiments/01_joint_episode.py](05_data_recording/experiments/01_joint_episode.py) | `./lekiwi basic --chapter 5` | 명령 전 상태 → 명령 → 다음 상태를 JSON 기록·재생 |

### 6장: 설정 파일이 변환·학습 실행기에 일을 요청합니다

아래 파일은 **호스트 `python3`**로 실행합니다. 내부의 `lekiwi`가 필요한 Docker 환경을 사용합니다.

| 파일 | 명령 (`python3` 다음에 넣을 경로) | 내가 정할 값 | 결과 |
|---|---|---|---|
| [02_dataset_list.py](06_lekiwi_dataset/experiments/02_dataset_list.py) | `isaacsim_basic/06_lekiwi_dataset/experiments/02_dataset_list.py` | 없음 | 원본과 변환본 목록 |
| [03_convert_dataset.py](06_lekiwi_dataset/experiments/03_convert_dataset.py) | `isaacsim_basic/06_lekiwi_dataset/experiments/03_convert_dataset.py` | 실제 episode_ids, 새 dataset_name, success_only | LeRobot 데이터셋 |
| [04_inspect_dataset.py](06_lekiwi_dataset/experiments/04_inspect_dataset.py) | `isaacsim_basic/06_lekiwi_dataset/experiments/04_inspect_dataset.py` | 같은 dataset_name | 검사 결과 JSON |
| [06_train_act.py](06_lekiwi_dataset/experiments/06_train_act.py) | `isaacsim_basic/06_lekiwi_dataset/experiments/06_train_act.py` | 입력 데이터, 새 run_name, 학습 설정 | 모델·전후처리 설정·결과 JSON |
| [07_infer_act.py](06_lekiwi_dataset/experiments/07_infer_act.py) | `isaacsim_basic/06_lekiwi_dataset/experiments/07_infer_act.py` | 같은 run_name, checkpoint, device, seconds | 가상 로봇의 모델 실행 |
| [05_upload_dataset.py](06_lekiwi_dataset/experiments/05_upload_dataset.py) | `isaacsim_basic/06_lekiwi_dataset/experiments/05_upload_dataset.py` | dataset_name, 본인 repo_id, 공개 범위 | 선택한 Hub 저장소에 공유 |

예를 들어 목록은 다음 한 줄로 실행합니다.

```bash
python3 isaacsim_basic/06_lekiwi_dataset/experiments/02_dataset_list.py
```

숫자는 파일을 구분하는 이름입니다. 현재 수업의 권장 실행 순서는 **02 → 03 → 04 → 06 → 07**, 공유할 때만 05입니다.

## 2. 1~3장의 파일을 읽는 순서

처음에는 모든 줄을 위에서부터 외우기보다 **`build_scene()` 안에서 방금 마우스로 바꿨던 속성**을 찾습니다.
그다음 `main()`에서 언제 그 함수가 호출되는지 확인합니다.

| 코드 | 역할 |
|---|---|
| 맨 위 `""" ... """` | 파일의 목적·실행·관찰 방법을 적은 설명 |
| `def build_scene(stage):` | 장면을 만드는 작업에 이름을 붙인 함수 정의 |
| `build_scene(stage)` | 정의된 작업을 실제로 실행하는 호출 |
| `stage` | 현재 장면. World·물체·관절 등이 들어 있음 |
| `prim` | 장면 안의 객체 하나. `/World/PracticeCube` 같은 경로로 찾음 |
| `main()` | 앱 시작과 장면 생성, 창 유지·종료를 연결 |
| `if __name__ == "__main__":` | 이 파일을 프로그램으로 실행할 때 아래 main()을 호출하는 입구 |

`def` 줄을 읽었다고 즉시 물체가 만들어지는 것은 아닙니다. 다음처럼 **호출되는 순간**에 함수 안의 작업이 실행됩니다.

```text
실행기에서 파일 선택
  → main()
  → SimulationApp으로 Isaac Sim 시작
  → omni/pxr 가져오기
  → 새 Stage 준비
  → build_scene(stage) 호출로 객체·속성 생성
  → 초기 scene.usda 저장
  → Play/Stop을 사용하며 관찰
  → 창 종료
```

00_empty_stage.py는 직접 객체를 만들기 위한 파일이므로 build_scene()이 없습니다.
`SimulationApp`, 화면 유지 반복문, `app.close()`는 앱 실행을 위한 부분입니다.
파일 전체를 열린 Isaac Sim의 Script Editor에 그대로 붙여 넣지 않습니다. 현재 교재의 실행 방식은 위 명령을 사용합니다.

## 3. 한 줄의 코드와 화면 속 속성 연결하기

다음은 01_no_gravity.py의 **일부를 읽기 위한 예시**입니다. 이것만 별도 실행하는 코드 블록은 아닙니다.

```python
cube = UsdGeom.Cube.Define(stage, "/World/PracticeCube")
cube.CreateSizeAttr(.1)
cube.AddTranslateOp().Set(Gf.Vec3d(0, 0, .7))
UsdPhysics.RigidBodyAPI.Apply(cube.GetPrim())
body = PhysxSchema.PhysxRigidBodyAPI.Apply(cube.GetPrim())
body.CreateDisableGravityAttr(True)
```

| 줄에서 볼 부분 | 화면에서 했던 일 | 숫자·설정의 의미 |
|---|---|---|
| `Cube.Define` | Cube 만들기 | 객체 경로 `/World/PracticeCube` |
| `CreateSizeAttr(.1)` | Size 입력 | 한 변 0.1 m |
| `AddTranslateOp().Set(...)` | Transform의 Translate 입력 | X=0, Y=0, Z=0.7 m |
| `RigidBodyAPI.Apply` | Add → Physics → Rigid Body | 힘에 반응하는 물체 |
| `CreateDisableGravityAttr(True)` | Disable Gravity 체크 | 중력 제외를 켜므로 큐브가 떨어지지 않음 |

`DisableGravity`는 **중력을 끄는 설정**입니다. 따라서 True가 중력 OFF, False가 중력 ON입니다.
`.1`은 `0.1`과 같은 숫자입니다. `Gf.Vec3d(x, y, z)`는 세 방향의 값을 묶은 표현입니다.
`GetPrim()`은 Cube라는 형상에서 그 아래 USD 객체를 가져와 물리 속성을 붙일 때 사용합니다.

## 4. 주석을 바꿀 때 확인할 것

`#` 뒤의 내용은 실행되지 않는 설명입니다. 비교할 줄을 바꿀 때는 기본 줄 앞에 `#`를 붙이고 사용할 줄의 `#`를 지웁니다.

```python
# body.CreateDisableGravityAttr(True)
body.CreateDisableGravityAttr(False)
```

같은 속성을 설정하는 두 줄을 모두 켜면 뒤에서 설정한 값이 적용됩니다.
함수 안에 있던 줄의 **앞쪽 공백은 유지**합니다. Python은 공백으로 어느 작업 안에 속하는지 구분합니다.

학생 파일 수정 순서는 **실행 종료 → 값 하나 변경 → Ctrl+S → 같은 파일을 여는 명령 → 결과 비교**입니다.
`isaacsim_basic/*/experiments/*.py` 수정은 다음 실행에 반영됩니다.
`isaac_sim/keyboard_drive.py` 같은 공통 코드 수정은 해당 교재 안내대로 `./lekiwi setup sim`이 필요합니다.

## 5. 질량·마찰·반발 코드에서 반복되는 도우미

04_mass_gravity.py, 05_friction.py, 06_restitution.py에는 다음 함수가 있습니다.

| 함수 | 왜 나누었는가 |
|---|---|
| `box()` | 위치·크기·색상을 받아 같은 상자 생성 과정을 반복 사용 |
| `material()` | 정지 마찰·동적 마찰·반발계수를 한 물리 재질로 묶음 |
| `bind()` | 재질을 실제 물체에 연결 |
| `build_scene()` | 이번 실험에서 어떤 물체·값을 사용할지 결정 |

질량 실험에서는 `box()`를 사용하고 `material()`·`bind()`는 호출하지 않습니다.
처음에는 도우미 함수 본문보다 build_scene()의 **Low/High 또는 Light/Heavy 두 설정**을 비교하세요.

마찰·반발은 접촉하는 양쪽 물체에 같은 재질을 연결해 비교합니다. 마찰 실험에서는 큐브와 경사면, 반발 실험에서는 공과 받침대입니다.
마찰 실험의 `math.sin`·`math.cos`는 큐브를 경사면 위에 올려놓을 위치 계산입니다. 첫 마찰 비교에서는 이 계산을 그대로 둡니다.

## 6. 관절과 카메라 코드에서 관찰할 것

2장의 build_scene()은 **몸체 생성 → 받침 고정 → 두 몸체 사이 회전 관절 → Drive** 순서입니다.
`Body0`·`Body1`은 연결할 몸체, `LocalPos0`·`LocalPos1`은 각 몸체 기준의 접점입니다.
Drive의 TargetPosition은 목표 각도이며, 힘·관절 제한·물리 계산을 거쳐 실제 자세가 정해집니다.

| 항목 | 이번 코드의 단위·역할 |
|---|---|
| 위치·크기 | m |
| 질량 | kg |
| USD Angular Drive 목표·관절 한계 | degree(도) |
| 보충 예제의 `ArticulationAction`·읽은 관절 상태 | rad(라디안) |
| `np.deg2rad(30)` | 30도를 제어기가 읽는 라디안 값으로 변환 |

3장의 카메라는 먼저 생성하고, Viewport의 카메라 목록에서 선택해야 그 시점으로 봅니다.
`SetLookAt`의 세 인자는 **카메라 위치·바라볼 점·위쪽 방향**입니다.
같은 위치·같은 카메라에서 FocalLength 24와 48을 비교해야 렌즈 변화의 영향을 구분할 수 있습니다.
이 장의 큐브는 정적 관찰 대상이며 Play로 떨어지는 예제가 아닙니다.

## 7. 기록 코드: 한 프레임에 무엇이 들어가는가

5장 기록은 [01_lekiwi_recording.py](06_lekiwi_dataset/experiments/01_lekiwi_recording.py)의 `RecordingPanel`이 관리합니다.
이 클래스 이름 때문에 별도 Record 패널을 찾을 필요는 없습니다. 화면의 상태 표시와 F5/F6/F7/F9로 진행합니다.

```text
before_step: 시각 t의 관측 상태 + 행동 준비
  → 가상 로봇에 행동 적용, 물리 계산 1/30초 진행
  → after_step: 시각 t+1/30의 다음 상태 추가
  → 같은 시각 t에 촬영한 front·wrist 영상과 연결
  → EpisodeWorker가 파일에 기록
```

- `snapshot()`은 영상의 실제 촬영 시각을 확인합니다. 파일을 읽은 시각으로 대신하지 않습니다.
- `accept_capture()`는 영상과 관측의 시각이 맞는 한 프레임을 저장 작업자에게 넘깁니다.
- `handle_key()`는 시작·종료·저장 요청을 넣고, 실제 처리는 물리·파일 작업 흐름에서 수행합니다.
- `poll_io()`는 파일 쓰기가 끝났는지 확인합니다. 따라서 F7/F9를 눌렀다고 바로 SAVED가 되는 것은 아닙니다.

학생이 먼저 바꿀 값은 `task_description`과 `self.duration_seconds`입니다.
명령 앞의 `LEKIWI_RECORD_TASK`·`LEKIWI_RECORD_SECONDS` 값이 있으면 그것이 코드 기본값보다 우선합니다.
영상 정렬·오류 검사 코드는 첫 실습에서는 그대로 두고, 저장한 manifest와 두 영상에서 결과를 확인합니다.

## 8. 변환·학습 파일: 짧은 코드로 큰 작업이 실행되는 이유

6장의 02~07번 파일은 학습 알고리즘 전체가 아니라 **설정과 실행을 연결하는 파일**입니다.

| 표현 | 뜻 |
|---|---|
| `dataset_name = '...'` | 변환본을 찾을 이름. 따옴표는 문자열 표시 |
| `episode_ids = ['...', '...']` | 여러 원본 id를 담은 목록. 대괄호와 항목 사이 쉼표 사용 |
| `True` / `False` | 켜기·끄기 같은 논리값. 따옴표 없이 사용 |
| `None` | 이번 설정을 지정하지 않음. 빈 문자열 `''`과 다름 |
| `launcher = ... / 'lekiwi'` | 이 저장소의 실행 명령 파일을 찾음 |
| `command = [...]` | 실제로 실행할 명령과 인자를 목록으로 구성 |
| `subprocess.run(command)` | 그 명령을 별도 프로세스로 실행하고 완료까지 기다림 |
| `SystemExit(result.returncode)` | 실제 작업 결과를 전달. 종료 코드 0은 성공, 다른 값은 실패 |

예를 들어 06_train_act.py에서 `steps=1`을 정하면 main()이 `--steps 1` 인자로 바꿔 학습기에 전달합니다.
`main()` 아래의 실행문은 유지하고 파일 위쪽 설정을 고치는 방식으로 실습합니다.

```text
5장 원본 에피소드
  → 03_convert_dataset.py: 두 영상 MP4 + 상태·행동 Parquet + 메타데이터·통계
  → 04_inspect_dataset.py: 변환본을 실제로 다시 읽어 검사
  → 06_train_act.py: 영상·상태로 행동을 예측하도록 ACT 학습
  → 07_infer_act.py: 저장한 모델로 같은 맵의 가상 로봇 조작
```

03번이 저장하는 `dataset_name`은 04·06번에서 동일하게 사용합니다.
06번이 저장하는 `run_name`은 07번에서 동일하게 사용합니다. 데이터 이름과 모델 결과 이름은 역할이 다릅니다.
기본 1회 학습은 계산과 저장 확인용입니다. 추론 때는 추가 학습을 하지 않으며, 집기 성공은 별도로 평가합니다.

## 9. 실행 전·후 스스로 확인하기

실행 전에는 **어떤 파일인지, 어떤 장면·작업을 여는지, 바꾼 값이 무엇인지** 확인합니다.
실행 뒤에는 **화면 또는 출력에서 바뀐 결과**를 확인합니다.

| 헷갈리는 상황 | 먼저 확인할 것 |
|---|---|
| 수정해도 이전 결과가 나옴 | Ctrl+S, 실행한 파일 경로, 바꾼 줄보다 뒤에 같은 속성을 다시 설정했는지 |
| `omni` 또는 `pxr`를 찾지 못함 | 1~3장 파일을 호스트 python3로 실행했는지; 표의 `./lekiwi basic` 사용 |
| 카메라 값을 바꿨는데 화면이 같음 | Viewport에서 실제 `/World/Camera`를 선택했는지 |
| 4장인데 막대 하나만 나옴 | 보충 `basic --chapter 4`인지; 본 수업은 교재의 scene/teleop 명령 |
| 5장인데 JSON 하나만 나옴 | 관절 보충 예제인지; 본 수업은 같은 코스에서 teleop --record |
| 변환·학습 입력을 찾지 못함 | 실제 id, dataset_name, run_name의 연결과 이전 단계 완료 여부 |

[전체 목차로 돌아가기](README.md)
