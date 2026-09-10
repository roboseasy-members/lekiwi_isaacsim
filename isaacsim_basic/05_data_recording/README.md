# 5편 · Python으로 관절 에피소드 기록·저장·재생

한 관절의 상태와 명령을 JSON으로 저장하며 에피소드의 구조를 배웁니다.
본격적인 LeKiwi RGB 학습 데이터는 6편에서 수집합니다. 이 장의 JSON은 LeRobot 학습 입력이 아닙니다.

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


## 1. 기본 기록 실행

[01_joint_episode.py](experiments/01_joint_episode.py)

```bash
./lekiwi basic --chapter 5
```

실행하면 자동으로 3초의 가상 움직임을 기록하고 일시정지합니다. 전용 Record 버튼이나 Lesson 탭은 없습니다.
터미널에서 `STUDENT_RECORD saved=... frames=180`을 확인합니다.
파일 경로는 실행마다 새 폴더를 사용하므로 이전 에피소드를 덮어쓰지 않습니다.

![가상 관절 기록 후 기본 화면](images/08-code-first.png)

## 2. 한 프레임의 순서 읽기

`record()`의 반복문에서 다음 순서를 찾습니다.

```python
before = robot.get_joint_positions().tolist()
time, step = world.current_time, world.current_time_step_index
robot.apply_action(ArticulationAction(joint_positions=np.array([target])))
world.step(render=True)
after = robot.get_joint_positions().tolist()
logger.add_data({"frame_index": index, "observation": before,
                 "action": [target], "next_observation": after,
                 "next_time": world.current_time}, step, time)
```

관측은 **명령 전 t**, action은 **t에서 적용하는 목표**, 후속 관측은 **t+1/60초**입니다.
명령과 실제 관절각은 다를 수 있습니다. DataLogger는 우리가 전달한 딕셔너리와 물리 시각을 기록합니다.

`World(physics_dt=1/60, rendering_dt=1/60)`에서 한 번의 step은 물리 1/60초입니다.
벽시계의 3초와 반드시 같지는 않습니다. 느린 GPU에서는 같은 180프레임에 더 오래 걸릴 수 있습니다.

## 3. 기록 길이와 명령 바꾸기

`range(180)`을 360으로 바꾸면 6초입니다. 목표 식의 분모 180을 유지하면 같은 주기를 두 번 반복합니다.
진폭 .5를 주석 처리하고 .25 줄을 해제해 최대 목표 각도를 절반으로 줄입니다.
새 JSON의 action과 observation이 어떻게 달라지는지 비교합니다.
기록 중 표준 Pause/Stop을 누르면 불완전한 시간 연결을 저장하지 않도록 오류로 중단합니다.

## 4. 저장된 명령 재생

파일 아래 `main()`의 두 줄을 주석 해제합니다.

```python
path = record(world, robot, app, output)
if path is not None:
    replay(world, robot, app, path)
```

재실행하면 기록을 마친 뒤 `world.reset()`으로 모형을 초기화하고 파일의 action을 순서대로 적용합니다.
터미널의 `STUDENT_REPLAY frames=180 max_error_rad=...`를 확인합니다.
`replay()`는 `set_joint_positions`로 관측 상태를 강제로 복원하지 않습니다. 실제 PhysX에 같은 목표를 다시 전달합니다.

다음으로 기본 `record(...)` 호출을 주석 처리하고 파일 아래의 `Path("...episode.json")`, `replay(...)` 두 줄을 사용합니다.
경로의 예시 부분은 실제 저장 경로로 바꿉니다. 이 방법은 이전 실행의 JSON도 재생합니다.

## 5. 파일 열기

Docker의 `/data/...`는 호스트 저장소의 `data/...`와 연결됩니다.
터미널에 나온 파일을 편집기에서 열고 최상위 `Isaac Sim Data` 목록의 첫 두 프레임을 비교합니다.

| 항목 | 의미 |
|---|---|
| current_time / current_time_step | 명령 직전 물리 시각·스텝 |
| data.frame_index | 0부터 시작하는 기록 번호 |
| data.observation | 명령 직전 실제 관절각, rad |
| data.action | 목표 관절각, rad |
| data.next_observation | 한 물리 스텝 뒤 실제 각도 |
| data.next_time | 후속 상태의 물리 시각 |

프레임 i의 `next_observation`이 i+1의 `observation`과 같은지 확인합니다.
마지막 프레임의 후속 상태를 빼면 마지막 명령이 무엇을 만들었는지 확인하기 어렵습니다.

## 6. 학습 데이터와의 차이

이 예제는 움직임을 사인 함수로 정합니다. 사람이 시연한 성공 작업도, 카메라 이미지도 없습니다.
JSON을 저장했다는 사실만으로 학습에 충분한 데이터가 되지는 않습니다.
6편에서는 두 RGB, 6개 팔 관절, 베이스 명령, 작업 설명과 성공 여부를 함께 기록하고 LeRobot 형식으로 변환합니다.

[기록지](worksheet.md)에 180/360프레임, .5/.25 진폭, 저장·재생 오차와 실제 경로를 남깁니다.

[공식 자료](SOURCES.md) · [다음: 6편](../06_lekiwi_dataset/README.md)
