# 브라우저에서 코드를 수정하며 원격 수업하기

연구실 데스크탑이 Isaac Sim을 실행하고, 학생 Ubuntu 노트북은 브라우저 편집기와 WebRTC 화면을 엽니다.
편집기는 별도 **code-server Docker 컨테이너**입니다. VS Code 기반의 브라우저 편집기로, Microsoft 배포판과 확장 마켓은 다릅니다.
Isaac Sim을 종료해도 편집기는 유지됩니다. 이 기능은 현재 `feature/remote_classroom`에서 제공합니다.

처음 접속할 때는 [0장 환경 설정](../isaacsim_basic/00_env_setting/README.md)부터 진행합니다.
학생마다 자기 계정으로 배정된 데스크탑·노트북을 연결하고, 같은 **데스크탑 Tailscale IPv4**를 실행기·SSH·영상 클라이언트에 사용합니다.
이후에는 아래 절차로 수업을 시작합니다. 같은 LAN에서 사용할 때는 접속 가능한 데스크탑 LAN 주소를 사용할 수 있습니다.

## 1. 데스크탑에서 한 번 준비

[설치 안내](../README.md)에 따라 Isaac Sim 설치·실행 검사를 완료합니다.
이 변경이 포함된 코드로 다음 이미지를 준비합니다. 노트북에는 Isaac Sim 이미지를 설치하지 않습니다.

```bash
export ACCEPT_EULA=Y
./lekiwi setup all
./lekiwi remote setup-editor
```

`docker info`에 권한 오류가 나지만 `sudo docker info`는 성공한다면, 실행 전 같은 터미널에
`export LEKIWI_DOCKER_SUDO=1`을 설정합니다. `./lekiwi` 전체를 sudo로 실행하지 않습니다.

## 2. 데스크탑에서 수업 편집기 시작

기존 Isaac Sim 실습을 정상 종료합니다. AnyDesk로 연 데스크탑 터미널에서 다음을 실행합니다.
아래 주소는 예시이므로 **데스크탑에서 `tailscale ip -4`로 확인한 주소로 바꿉니다**.

```bash
export ACCEPT_EULA=Y
./lekiwi remote workspace --host 100.80.10.20
```

브라우저 로그인용 비밀번호를 12자 이상으로 정해 숨김 입력합니다.
비밀번호는 실행 중 메모리에서 사용하며 파일·명령 인자에 저장하지 않습니다. 실행기를 다시 켤 때 새로 입력합니다.
`LEKIWI_WORKSPACE ready url=http://127.0.0.1:8080`가 나오면 준비된 것입니다.
수업 중 이 터미널을 유지합니다. Docker에 sudo를 쓰는 경우 실행기가 열린 동안만 해당 터미널의 인증을 갱신합니다.

## 3. 노트북에서 SSH 연결 후 편집기 열기

데스크탑은 SSH 서버가 필요합니다. 처음 한 번 데스크탑에서 준비합니다.

```bash
sudo apt install openssh-server
sudo systemctl enable --now ssh
```

노트북의 로컬 터미널에서 아래 명령을 실행합니다. `사용자명`은 **데스크탑 Ubuntu 로그인 계정**이고,
주소는 편집기 실행에 사용한 데스크탑 Tailscale IP로 바꿉니다. 첫 접속에서는 서버 키를 확인하고 데스크탑 계정으로 인증합니다.

```bash
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L 127.0.0.1:8080:127.0.0.1:8080 사용자명@100.80.10.20
```

이 명령이 오류 없이 대기하면 연결된 것입니다. **수업 동안 이 터미널을 유지합니다.**
노트북 Chrome에서 **http://127.0.0.1:8080**을 열고 2절에서 정한 편집기 비밀번호로 로그인합니다.
8080은 데스크탑의 외부 네트워크에 공개하지 않으며, 노트북과 데스크탑 사이의 통신은 SSH로 암호화됩니다.
코드·터미널과 교재 미리보기 모두 같은 주소에서 작동하고 별도 인증서 설치는 필요하지 않습니다.

`Address already in use`이면 기존 터널을 확인합니다. 임의로 다른 프로세스를 종료하지 않습니다.
노트북의 8080을 이미 사용한다면 `-L 127.0.0.1:8081:127.0.0.1:8080`으로 바꾸고 브라우저에서는 `http://127.0.0.1:8081`을 엽니다.
데스크탑 편집기 포트 자체를 변경했다면 `remote workspace --port 번호`와 SSH 명령의 마지막 포트를 맞춥니다.

표준 VS Code 작업 영역 신뢰 확인이 나오면 본인이 받은 수업 파일을 확인하고 신뢰를 선택합니다.
왼쪽 `교재와 Python 실습`에서 다음 파일을 엽니다.

```text
01_object_physics/README.md
```

각 장 README는 파일을 연 뒤 `Ctrl+Shift+V`로 이미지가 포함된 미리보기를 볼 수 있습니다.
메뉴 `Terminal → New Terminal`로 편집기 아래 터미널을 엽니다.

## 4. 빈 편집 화면을 열고 마우스 실습 시작

**브라우저 편집기 안의 터미널**에서 실행합니다.

```bash
lesson run --file /workspace/isaacsim_basic/01_object_physics/experiments/00_empty_stage.py
```

실행은 즉시 시작되지만 GPU 준비는 시간이 걸립니다. 상태를 확인합니다.

```bash
lesson status
```

`READY`가 나오면 노트북의 [공식 Isaac Sim 5.1 WebRTC 클라이언트](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/download.html)를 열고,
Server에 **같은 데스크탑 IP**를 입력해 Connect합니다. 빈 Stage와 격자가 보이면 1장 본문에서 바닥·물체를 직접 만드는 실습을 시작합니다.
브라우저는 코드와 터미널, WebRTC 클라이언트는 Isaac Sim 화면을 담당합니다.

오래 기다려도 준비되지 않거나 `FAILED`이면 `lesson logs`로 확인합니다.
출력된 데스크탑의 `data/remote/session.*/sim.log`에 전체 Isaac Sim 로그가 있습니다.

## 5. 장 마지막에서 코드 수정 → 저장 → 재실행

각 장의 마우스 실습과 USD 저장을 마친 뒤 진행합니다. 1장에서는
`01_object_physics/experiments/01_no_gravity.py`를 열고 본문 마지막의 코드 설명을 읽습니다.

1. 예제의 파란색 기본 줄을 주석 처리하고 바로 아래 주황색 줄을 해제합니다.
2. `Ctrl+S`로 저장합니다.
3. 브라우저 터미널에서 현재 실습을 종료합니다.

```bash
lesson stop
```

`STOPPED`를 확인한 다음 같은 파일을 다시 실행합니다.

```bash
lesson run 1
```

`READY` 후 WebRTC에서 다시 Connect하여 색상이 달라졌는지 확인합니다.
Isaac Sim 화면의 Play/Stop은 물리 시뮬레이션을 조절합니다. **Python 변경은 프로세스를 재실행해야 반영됩니다.**
실행 중 `lesson run`을 다시 보내면 중복 실행을 막고 먼저 종료하도록 안내합니다.
기록 중인 경우 저장·폐기를 마친 뒤 `lesson stop`을 사용합니다.

## 6. 나머지 장과 직접 만든 파일

각 장은 README의 마우스 실습부터 진행합니다. 아래 표는 마지막 코드 실습에서 사용할 실행 명령입니다.

| 목적 | 브라우저 터미널 명령 |
|---|---|
| 2~6장 기본 파일 | `lesson run 2`부터 `lesson run 6` |
| 1장 비교 예제 1~6 | `lesson run --experiment 2` 등 |
| 직접 선택한 파일 | `lesson run --file 01_object_physics/experiments/01_no_gravity.py` |
| 실행 상태 / 최근 로그 | `lesson status` / `lesson logs` |
| 현재 실습 종료 | `lesson stop` |

실행 가능한 파일은 각 장의 `experiments/` 바로 아래 `.py`입니다. 새 파일도 여기에 만듭니다.
`--file`은 편집기 터미널의 현재 폴더를 기준으로 해석합니다. 위 예시는 기본 터미널 위치에서 실행합니다.
표준 메뉴 `Terminal → Run Task → 현재 Python 실습 실행`으로 열어 둔 파일을 실행할 수도 있습니다.
장 번호와 1장의 실험 번호는 다릅니다.

편집기 컨테이너에 Isaac Sim Python은 없습니다. `python3 파일.py` 대신 `lesson run`을 사용해야
Isaac Sim 컨테이너의 `SimulationApp`, `pxr`, `omni`를 사용할 수 있습니다.

6장에서 노트북의 실제 리더 입력을 받으려면 다음 명령으로 시작합니다.

```bash
lesson run 6 --teleop
```

리더 접속 문구를 별도로 정해 숨김 입력하고, 노트북에서 같은 문구로
[리더암 준비·연결 절차](remote-classroom.md#4-노트북에-리더암-환경-준비)를 진행합니다.
리더 실습의 정확한 설치·안전 확인·연결 명령은 해당 문서의 4~5절을 따릅니다.
USB 리더암은 화면을 받는 **노트북**에 연결합니다. 브라우저 편집기에서 USB 장치를 열지 않습니다.

기록 작업 설명은 `06_lekiwi_dataset/experiments/01_lekiwi_recording.py` 상단의
`task_description`에서 수정합니다. `Ctrl+S`로 저장하고 위 명령으로 실행하면 서버의 Isaac Sim이
수정한 코드를 읽습니다. 이 설명은 저장한 에피소드의 `task`와 변환한 학습 데이터에 전달됩니다.
기존 실습이 실행 중이면 기록의 저장·폐기 후 `lesson stop`을 하고 재실행합니다.

브라우저 터미널은 **서버의 편집기 컨테이너**에서 동작합니다. `lesson run`이 서버의 Isaac Sim 컨테이너를
헤드리스 송출 모드로 실행하고, 노트북은 WebRTC 클라이언트에서 화면을 받습니다.
브라우저 편집기 접속과 WebRTC 화면 연결은 별도이므로 `READY` 확인 후 서버 IP로 Connect합니다.

6장 기록 화면 왼쪽 위에는 수집 상태, 현재 에피소드 시간/최대 시간, 프레임 수가 표시됩니다.
F5에서 빨간 `REC`, F6 이후 `STOPPED / NOT SAVED`, F7/F9 저장 완료 후 `SAVED`를 확인합니다.
표시 시간은 수집한 프레임 기준의 시뮬레이션 시간입니다. 이 UI는 학습용 카메라 영상에 포함되지 않습니다.

## 7. Python 파일을 수정하고 데이터 변환·검사

6장에서 F6으로 수집을 마치고 F7(연습) 또는 F9(성공)로 저장합니다. `SAVED`를 확인한 뒤 진행합니다.
왼쪽 탐색기에서 `06_lekiwi_dataset/experiments`를 열면 다음 파일이 있습니다.

| 파일 | 학생이 수정할 값 | 실행 결과 |
|---|---|---|
| `02_dataset_list.py` | 없음 | 저장된 시연의 id·작업 설명·프레임 수와 데이터셋 목록 |
| `03_convert_dataset.py` | `episode_ids`, `dataset_name`, `success_only` | 선택한 시연을 새 LeRobot 데이터셋으로 변환·기본 검사 |
| `04_inspect_dataset.py` | 변환할 때 사용한 `dataset_name` | 상태·영상 재열기 검사와 학습 입력 경로 |
| `05_upload_dataset.py` | `dataset_name`, `repo_id`, `private` | 검사된 데이터셋을 Hugging Face에 선택 업로드 |
| `06_train_act.py` | `dataset_name` 또는 `repo_id`, `run_name`, `steps`, `batch_size` | 공식 ACT 학습과 모델 저장 |
| `07_infer_act.py` | 학습 때의 `run_name`, `checkpoint`, `device`, `seconds` | 저장한 ACT로 Isaac Sim 추론 준비 |

**브라우저 VS Code의 새 터미널**은 `isaacsim_basic` 폴더에서 열립니다. 처음 한 번 6장 폴더로 이동하고 목록을 실행합니다.

```bash
cd 06_lekiwi_dataset/experiments
python3 02_dataset_list.py
```

`03_convert_dataset.py`를 편집기로 열어 상단의 설정을 수정합니다. 목록의 실제 `id`를 따옴표 안에 복사합니다.
아래 `SESSION/EPISODE`는 자리 표시자이므로 그대로 사용하지 않습니다.

```python
episode_ids = [
    'lekiwi.SESSION/episode.EPISODE',
]
dataset_name = 'basket_01'
success_only = False
```

여러 에피소드를 묶으려면 `episode_ids`에 쉼표로 구분해 한 줄씩 추가합니다.
`success_only = True`는 F9로 성공 표시한 시연만 포함합니다. F7 연습 기록을 변환하는 저장 검사에서는 `False`를 유지합니다.
집기에 실패한 기록과 표시 검사만 한 기록은 본 학습용 선택에서 제외합니다.

`Ctrl+S`로 저장하고 **같은 터미널에서 파일명만 지정하여 실행**합니다. 변환 설정을 터미널 인자로 쓰지 않습니다.

```bash
python3 03_convert_dataset.py
```

서버의 LeRobot 컨테이너가 변환·검사하고 터미널에 경과 시간과 완료 결과를 표시합니다.
`LEKIWI_DATASET_JOB result=PASS`와 프레임·에피소드 수를 확인합니다. 원본은 유지하며 같은 출력 이름을 덮어쓰지 않습니다.
다시 변환할 때는 스크립트의 `dataset_name`을 새 이름으로 바꿉니다.

`04_inspect_dataset.py`의 `dataset_name`도 같은 이름으로 수정하고 저장한 뒤 실행합니다.

```bash
python3 04_inspect_dataset.py
```

이 네 파일은 **`python3`로 실행**합니다. `lesson run`이나 ‘현재 Python 실습 실행’ 작업은 Isaac 장면 파일용입니다.
스크립트 아래쪽의 `lesson` 호출 코드는 브라우저에서 서버로 설정을 보내는 연결 부분이며 수업 중 수정하지 않아도 됩니다.

작업은 한 번에 하나만 실행됩니다. 다른 브라우저 터미널에서 아래 명령으로 상태와 진행 단계·오류를 확인할 수 있습니다.

```bash
lesson dataset status
lesson dataset logs
```

`RUNNING`은 진행 중, `SUCCEEDED`는 성공, `FAILED`는 실패입니다. 로그의 `VALIDATING_RAW`, `ENCODING`, `CHECKING_VIDEOS`는
각각 원본 검사·영상 변환·변환 후 영상 검사를 뜻합니다. 경과 시간은 작업을 기다린 실제 시간이며 6장 수집 화면의 에피소드 시간과 다릅니다.

브라우저 터미널을 닫거나 Ctrl+C를 눌러도 서버 작업은 계속됩니다. 같은 편집기 실행에 다시 연결하고
`lesson dataset status`로 확인합니다. `lesson stop`은 Isaac 실습만 종료합니다.
**데스크탑의 `remote workspace`를 종료하면 진행 중인 변환도 종료되므로, 수업 종료 전 성공·실패 상태를 확인합니다.**
중간에 종료된 변환은 완성된 데이터셋으로 쓰지 않고 원본에서 새 이름으로 다시 변환합니다.

변환된 파일은 왼쪽 탐색기의 **LeRobot 데이터셋**에서 읽을 수 있습니다. 실제 저장 위치는 서버의 `data/datasets/basket_01/`이고,
컨테이너 경로는 `/data/datasets/basket_01`입니다. 로컬 학습에는 업로드가 필요하지 않습니다.
선택 업로드가 필요하면 `05_upload_dataset.py` 상단에서 로컬 이름, `계정명/저장소명`, 공개 범위를 수정해 저장하고 실행합니다.
기본값 `private = False`는 공개 업로드입니다. 비공개가 필요하면 `True`로 바꿉니다.

```bash
python3 05_upload_dataset.py
```

쓰기 토큰은 실행 중 숨김 입력합니다. 코드·명령행·로그에는 저장되지 않습니다. 검사 완료 데이터의 학습 파일과 자동 생성한 카드를 업로드하며,
로컬 경로가 든 `recording_report.json`은 제외합니다. 새 저장소 이름을 사용하며 기존 데이터·버전 태그가 있으면 중단합니다.
모든 학습 파일·카드와 LeRobot용 `v3.0` 태그를 확인한 뒤 Hugging Face 주소와 `LEKIWI_DATASET_JOB result=PASS`를 출력합니다.
학습은 `06_train_act.py`와 `lesson train`으로 실행하고, [ACT 학습·추론 안내](../README.md#9-act-학습과-isaac-sim-추론)를 따릅니다.

이미 편집기를 사용 중이었다면 저장·작업 종료 후 서버에서 `./lekiwi setup lerobot`과 `./lekiwi remote setup-editor`를 실행하고
`remote workspace`를 다시 시작해야 새 명령과 탐색기 폴더가 반영됩니다. 학생의 스크립트 설정 수정에는 이미지 재빌드가 필요 없습니다.

## 8. 파일 저장 위치와 종료

- 편집한 Python: **데스크탑 저장소의 `isaacsim_basic/각장/experiments/`**. 편집기를 꺼도 남고, 코드 변경만으로 이미지 재빌드는 필요하지 않습니다.
- 교재·안내: 편집기에서는 읽기 전용입니다. Python 실습 폴더만 수정할 수 있습니다.
- 수업 기록: 데스크탑 `data/isaacsim_basic/`, LeKiwi 시연은 `data/recordings/`. 편집기의 결과 폴더에서 읽을 수 있습니다.
- 편집기 설정·실행 로그: 데스크탑 `data/web_classroom/`. Git에서 제외됩니다.
- 변환 결과: 데스크탑 `data/datasets/`. 편집기의 **LeRobot 데이터셋**에서 읽을 수 있습니다.
- 변환 작업 로그: 데스크탑 `data/web_classroom/datasets/dataset.*/`. `lesson dataset logs`로 확인합니다.
- 학습 명령은 기존 데스크탑 절차를 사용합니다. 편집기 터미널에는 실습 실행과 데이터 목록·변환·검사·선택 업로드가 연결됩니다.

수업 종료 시 기록을 저장하고 `lesson stop`을 실행합니다. 그 뒤 데스크탑에서 `remote workspace`를 실행한 터미널에 Ctrl+C를 보냅니다.
이 실행기가 만든 편집기와 실습만 종료합니다. 노트북 SSH 터미널도 Ctrl+C로 종료합니다. 브라우저 창만 닫으면 서버는 계속 실행됩니다.

편집기 접속에는 데스크탑의 SSH TCP 22가 필요합니다. 데스크탑의 8080을 공유기나 방화벽에 공개하지 않습니다. WebRTC·리더 입력 포트는 [원격 실습 안내](remote-classroom.md)를 따릅니다.
이 도구는 방화벽이나 공유기 설정을 자동 변경하지 않습니다.

구현은 [code-server 설치 문서](https://coder.com/docs/code-server/install)와
[SSH 접속·인증 안내](https://coder.com/docs/code-server/guide)를 참고하며, 공식 `ghcr.io/coder/code-server:4.137.0` 이미지를 사용합니다.

## 검증 기록 · 2026-09-11

- Ubuntu 서버 역할 노트북(RTX 3070 Laptop, 드라이버 580.173.02)에서 편집기 이미지를 빌드했습니다.
- 다른 Ubuntu 노트북의 Chrome에서 SSH 터널·로그인·교재 Markdown과 이미지 미리보기를 확인했습니다.
- 브라우저에서 1장 검증용 복사본의 색상 코드 주석을 바꿔 저장하고 `lesson stop` 뒤 재실행하여, WebRTC로 주황색 큐브를 확인했습니다. 원본 학생 코드는 유지했습니다.
- 최종 SSH 구성에서 원본 1장을 다시 실행하고 `READY` 및 1920×1080 영상 수신을 확인했습니다.
- 관련 소켓·실행 제어 테스트 53개 통과. 전체 회귀 테스트는 412개 통과, 호스트에 USD Python 모듈이 없는 7개 검사 제외.
- 위 편집기 검증에서는 2~6장 전체 실습 반복과 여러 학생 동시 접속을 수행하지 않았습니다.

### 원격 리더암·기록 추가 검증 · 2026-09-11

- 화면을 받는 Ubuntu 노트북의 USB SO101 리더를 토크 OFF로 연결하고, 서버의 가상 팔이 같은 방향으로 추종함을 사용자가 확인했습니다.
- Wi-Fi 입력 지연으로 추종이 해제되어 원격 가상 로봇의 입력 대기 한도를 500 ms로 조정했습니다. 200 ms가 넘게 지연된 응답 거부, 500 ms 초과 시 정지, 복구 후 R 재활성화 조건은 유지합니다. 로컬 USB 입력은 기존 250 ms입니다.
- `sudo` 실행 때도 원격 모드가 전달되도록 수정하고 서버 로그의 `input_timeout_ms=500`을 확인했습니다.
- 사용자가 F5로 시작하고 F6으로 종료한 연습 기록 1개를 F7로 저장했습니다. 30 FPS, 422프레임, 14.07초이며, front/wrist 각 422장의 이미지 해시·해상도·촬영 시각·상태 연결 검사를 통과했습니다. 관절 상태·명령의 실제 변화와 손목 영상의 시점 변화도 확인했습니다.
- 기록을 포함한 50초 관찰에서 추종 상태를 유지했고, 입력 단절은 관찰되지 않았습니다. 이 결과는 장시간 또는 여러 학생 동시 접속의 안정성 보장은 아닙니다.
- 이번 파일은 `success=false`인 원본 저장 검사 자료이며, LeRobot 변환·학습·정책 추론은 이 추가 검증에서 아직 실행하지 않았습니다.

### 수집 상태 표시 추가 검증 · 2026-09-11

- 같은 서버의 WebRTC 화면에서 F5 → F6 → F7 순서로 `RECORDING`, `STOPPED / NOT SAVED`, `SAVED`와 시간·프레임 수를 확인했습니다.
- 리더를 연결하지 않은 표시 검사에서 74프레임·2.47초의 연습 기록을 저장하고, 두 카메라의 이미지·시각·파일 검사를 통과했습니다. front/wrist 원본을 직접 열어 상태 표시가 영상에 포함되지 않는 것도 확인했습니다.
- 표시·기록·키 입력·화면 구성·파일 저장 관련 테스트 77개를 통과했습니다. 이 검사는 위의 실제 리더 시연 422프레임 검증과 별개입니다.

### 브라우저의 Python 파일로 변환·검사 · 2026-09-12

- Chrome에서 `02_dataset_list.py`를 실행해 기존 시연 3개의 목록을 확인했습니다.
- 편집기로 `03_convert_dataset.py`의 에피소드 ID·출력 이름을 수정하고 저장한 뒤, 터미널에서 `python3 03_convert_dataset.py`만 실행했습니다.
- 전날 실제 리더로 수집한 422프레임을 `leader_practice_20260912_01`로 변환했습니다. 24초 후 성공했고, 원본 프레임·해시·시각과 변환된 상태·두 영상을 검사했습니다.
- `04_inspect_dataset.py`의 이름을 맞춰 저장한 뒤 실행하여 8초 후 재열기 검사도 통과했습니다. LeRobot v3, 1개 에피소드, 30 FPS, 원본 보존을 확인했습니다.
- 브라우저 연결·학생 설정 파일·기존 변환·실행 관련 테스트 144개 통과(호스트 USD 모듈이 필요한 1개 제외). 원격 실습·원본 기록 관련 별도 회귀 테스트는 121개 통과(USD가 필요한 2개 제외).
- [실제 코드와 검사 화면](../isaacsim_basic/06_lekiwi_dataset/images/11-browser-dataset.png). 이 데이터는 `success=false`인 연습 기록이며, 학습과 추론은 아직 실행하지 않았습니다.

### 업로드 사전 재검토 · 2026-09-12

- 공개·비공개 업로드 명령이 서버에서 거절되는 문제를 재현했습니다. 브라우저 CLI가 불필요한 `public` 필드를 보내던 부분을 수정하고, 실제 CLI 파싱부터 서버 작업 생성까지 연결하는 테스트를 추가했습니다.
- 업로드 완료 파일 목록 전체를 확인한 뒤 `v3.0` 태그를 생성하고, 태그가 이번 업로드를 가리키는지 확인하도록 보완했습니다. 기존 데이터·버전 태그가 있는 저장소는 덮어쓰지 않습니다. [동작과 공식 근거](dataset-manager.md#선택-hugging-face에-업로드).
- 수정 후 전체 호스트 테스트 **470개 통과, 8개 제외**. 제외 사유는 USD 모듈 7개와 xacro 1개 미설치입니다. 로컬 소켓 검사는 실행 환경의 소켓 제한 밖에서 통과했습니다. Python·Bash 문법, `git diff --check`, 6장 Notion ZIP 무결성도 확인했습니다.
- 현재 작업 PC의 원본 시연 5개는 전체 프레임·이미지 해시·촬영 시각 검사를 통과했습니다. 로컬 변환 데이터 3개(99·1543·90프레임)는 모든 상태·행동 값의 유효성, Parquet 행 수와 두 카메라 영상의 전체 디코딩·프레임 수를 확인했습니다.
- 99·1543프레임 데이터는 원본과 변환본의 전체 상태·행동도 일치했습니다. 90프레임 데이터는 출처 기록의 원본 경로가 현재 PC에 없어 원본 대조를 완료하지 못했습니다. 원본 경로와 데이터는 변경하지 않았습니다.
- 위 브라우저 검증의 422프레임 데이터는 현재 작업 폴더에서 찾지 못했습니다. 이 호스트 사전 검토에서는 실제 Hugging Face 업로드와 LeRobot 컨테이너 재열기를 실행하지 않았으며, 이후 서버 확인·실제 업로드 결과는 아래에 기록했습니다.

### 서버 데이터 확인·실제 비공개 업로드 · 2026-09-12

- 실제 데이터는 RTX 3070 서버 `192.168.0.171`의 `/home/roboseasy/youn_ws/lekiwi_class_rehearsal/data/datasets/leader_practice_20260912_01`에서 확인했습니다. 개발 PC `192.168.0.81`의 데이터 폴더와 구분합니다.
- 원본은 서버의 `data/recordings/lekiwi.e6grgk7i/episode.e0r_snxp`입니다. 서버 Docker에서 읽기 전용으로 연결해 원본 전체 해시·시각 검사, LeRobot 재열기, 422프레임 전체 상태·행동 일치를 확인했습니다. front/wrist 영상은 각각 640×480·30 FPS·422프레임의 전체 디코딩을 통과했습니다.
- 변환 파일 8개를 개발 PC의 임시 폴더로 복사하고 서버 원본과 SHA-256이 모두 일치함을 확인했습니다. 검토한 현재 프로젝트의 데이터 관리 코드를 읽기 전용으로 연결한 Docker 컨테이너에서 업로드를 실행했습니다.
- [SJun99/leader-practice-test-20260912](https://huggingface.co/datasets/SJun99/leader-practice-test-20260912)에 **비공개**로 업로드했습니다. `v3.0` 태그와 업로드 커밋 `8049b5b1077123ef7008602612e5e0bddfc7bffb`가 일치함을 확인했습니다.
- Hub에서 `v3.0`을 새 임시 폴더로 내려받아 학습 파일 7개의 SHA-256 일치와 `recording_report.json` 제외를 확인했습니다. 내려받은 데이터를 LeRobot으로 다시 열어 **1개 에피소드·422프레임·30 FPS**와 처음·중간·마지막 상태·행동·두 RGB의 유효성을 확인했습니다.
- 이 데이터는 `success=false`인 연습 시연입니다. 이번 검증은 파일 업로드·재열기 검사이며 학습·추론·실제 장비 조작은 포함하지 않았습니다.
- 서버의 기존 브라우저 실습 소스·이미지는 이번 업로드에서 변경하지 않았습니다. 앞서 수정한 공개 범위 전달과 업로드 후 버전 태그 검사를 브라우저 실습에 적용하려면 해당 수정본 배포가 필요합니다.

### 데이터셋 카드·시각화 보완 · 2026-09-12

- 사용자가 저장소를 공개로 전환한 뒤 Visualize Dataset이 정상적으로 표시된다고 확인했습니다. Hub API에서도 `private=false`를 확인했습니다. 업로드 당시 비공개였던 상태와 구분합니다.
- 업로더가 `README.md`를 만들지 않아 카드가 없었습니다. 에피소드·프레임 수, 성공 표시 집계, 상태·행동·영상 규격과 시각화 링크를 담은 카드를 추가했습니다. 표 보기에는 `data/*/*.parquet`만 포함하여 다른 구조의 메타데이터 Parquet가 섞이지 않도록 했습니다.
- 실제 저장소에 카드 커밋 `a89b6a1aeede3cadb497172dc5062c262b0d12c3`을 업로드했습니다. Hub의 카드 메타데이터 검사, 내려받은 README 내용 일치, 기존 학습 파일 7개의 SHA-256 일치를 확인했습니다. 기존 `v3.0` 태그는 최초 학습 데이터 커밋을 그대로 가리킵니다.
- Hub에서 새 카드 설정으로 `datasets.load_dataset(..., split='train')`을 실행해 **422개 행·1개 에피소드**를 읽었습니다. 공개 범위 설정이나 학습 데이터는 카드 보완 작업에서 변경하지 않았습니다.
- 공개 저장소 페이지의 HTML에 카드 본문이 포함되는 것도 확인했습니다. 별도 일반 표 뷰어의 `/splits` API는 확인 시점에 HTTP 500(서버 혼잡·응답 준비 중)을 반환했으므로 그 화면의 정상 표시는 확인하지 못했습니다. 사용자가 정상 표시를 확인한 LeRobot Visualize Dataset과 구분합니다.
- 현재 프로젝트의 업로더는 새 업로드에 카드를 자동 생성하고 카드 포함 여부까지 확인한 다음 버전 태그를 붙이도록 수정했습니다. 관련 테스트 **110개 통과, 2개 제외**(호스트의 xacro·USD 모듈 미설치). 이 코드의 서버 실습 이미지 반영은 아직 하지 않았습니다.

### 공개 업로드 기본값·서버 이미지 반영 · 2026-09-12

- 사용자 요청에 따라 `05_upload_dataset.py`의 기본값을 `private = False`로 변경했습니다. `True`로 설정하면 비공개 업로드도 계속 사용할 수 있습니다.
- 서버 `/home/roboseasy/youn_ws/lekiwi_class_rehearsal`에 공개 기본값, 브라우저 CLI의 공개 범위 전달 수정, 카드 자동 생성·학습 파일 검사·`v3.0` 태그 생성을 반영했습니다. 교재와 6장 Notion ZIP도 갱신했습니다.
- 공식 Dockerfile로 `lekiwi-lerobot:browser-public-0912`, `lekiwi-editor:browser-public-0912`를 빌드하고 각 이미지의 `0.1.0`·`browser-upload-0912` 이름도 새 이미지로 연결했습니다. 기본 Compose 선택이 새 LeRobot 이미지를 사용하는지 확인했습니다.
- LeRobot 이미지 ID는 `sha256:b5f950f53ae0802a2e24d43c6907b4ee6e315e5129b994f7499c1110a4ff151a`, 편집기 이미지 ID는 `sha256:780768cc38c3490951a3f2cf1d5edc8d9b47ad53b3bbd4dbba930517cc6bc5d2`입니다.
- 새 LeRobot 이미지에서 기존 422프레임·두 영상을 실제 재열기하고, 네트워크가 차단된 테스트용 Hub 대체 객체로 공개 요청·카드·버전 태그 순서를 확인했습니다. 새 편집기 이미지에서는 학생 스크립트 기본값 → 설치된 `lesson` → Unix 소켓 → 서버 옵션 검증까지 통과했습니다. 이 배포 검사에서 새 Hub 저장소를 생성하거나 데이터를 다시 업로드하지 않았습니다.
- 관련 호스트 테스트 **110개 통과, 2개 제외**(xacro·USD 미설치), Python 문법·diff 검사와 Notion ZIP 검사를 통과했습니다. 실행 중인 컨테이너가 없어 수업 중단은 없었으며 검증용 컨테이너는 종료 후 제거됐습니다.
- 서버 소스 백업과 이미지 변경 기록은 `/tmp/lekiwi-public-deploy-3hg1rd7a`에 있습니다. 이전 이미지에는 각 기존 태그 뒤에 `-before-public-3hg1rd7a`를 붙인 이름을 남겼습니다. 실제 로봇 조작과 정책 학습·추론은 이번 작업에 포함하지 않았습니다.


### ACT 학습·추론 스크립트

6장 폴더의 `06_train_act.py`를 편집하고 저장한 뒤, 실행 중인 Isaac 실습을 `lesson stop`으로 종료합니다.
`python3 06_train_act.py`로 학습을 시작하고, 다른 터미널에서 `lesson train logs`로 진행·손실을 확인합니다.
`lesson train status`는 상태를, `lesson train stop`은 서버 학습 종료를 요청합니다.
학습 명령의 Ctrl+C는 화면 대기만 끝냅니다. 원본 데이터와 기존 결과는 보존합니다.

완료 결과는 탐색기의 **ACT 학습 결과**에 나타납니다.
추론 파일 `07_infer_act.py`의 `run_name`을 같은 이름으로 저장한 뒤 `python3 07_infer_act.py`를 실행합니다.
`lesson status`가 READY이면 WebRTC 화면에서 R로 시작합니다. Space 정지, F8 초기화, `lesson stop` 종료입니다.
이번 구현의 학습 검증 범위는 짧은 실행까지이며, 실제 추론과 전체 리허설은 후속 검증으로 남깁니다.
GPU·드라이버·CUDA 환경 준비와 충분한 성공 시연 수집은 별도 단계입니다.


### ACT 스크립트 실행 검사 · 2026-09-12

- `06_train_act.py` → `lesson train start` → 서버 실행기 → 공식 `lerobot-train` 연결을 구현했습니다. 옵션 전달·소켓·작업 수명은 호스트 테스트로 검사했습니다.
- 서버의 새 실행 경로 `./lekiwi act train`으로 기존 422프레임 데이터, 배치 1, 학습 1회, 무작위 ResNet18 초기화를 실행했습니다. 손실 84.275와 가중치 갱신, 모델·전후처리 파일 저장을 확인했습니다. 로컬 원본 데이터셋은 읽기 전용 마운트로 사용했습니다.
- 검사 결과는 서버 `data/outputs/act_script_check_20260912_01/`에 보관했습니다. 과제 성공률·본 학습·추론 동작을 검증한 결과는 아닙니다.
- `07_infer_act.py`는 같은 학습 결과의 모델·정규화·카메라·9개 상태/행동을 Isaac Sim에 연결합니다. 정지·지연·초기화 등은 하드웨어 없는 테스트로 검사했고, 실제 시뮬레이터 추론과 최종 리허설은 실행하지 않았습니다.
