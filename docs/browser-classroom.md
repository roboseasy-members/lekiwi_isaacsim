# 브라우저에서 코드를 수정하며 원격 수업하기

연구실 데스크탑이 Isaac Sim을 실행하고, 학생 Ubuntu 노트북은 브라우저 편집기와 WebRTC 화면을 엽니다.
편집기는 별도 **code-server Docker 컨테이너**입니다. VS Code 기반의 브라우저 편집기로, Microsoft 배포판과 확장 마켓은 다릅니다.
Isaac Sim을 종료해도 편집기는 유지됩니다. 이 기능은 현재 `feature/remote_classroom`에서 제공합니다.

## 1. 데스크탑에서 한 번 준비

[설치 안내](../README.md)에 따라 Isaac Sim 설치·실행 검사를 완료합니다.
이 변경이 포함된 코드로 다음 이미지를 준비합니다. 노트북에는 Isaac Sim 이미지를 설치하지 않습니다.

```bash
export ACCEPT_EULA=Y
./lekiwi setup sim
./lekiwi remote setup-editor
```

`docker info`에 권한 오류가 나지만 `sudo docker info`는 성공한다면, 실행 전 같은 터미널에
`export LEKIWI_DOCKER_SUDO=1`을 설정합니다. `./lekiwi` 전체를 sudo로 실행하지 않습니다.

## 2. 데스크탑에서 수업 편집기 시작

기존 Isaac Sim 실습을 정상 종료합니다. AnyDesk로 연 데스크탑 터미널에서 다음을 실행합니다.
아래 주소는 예시이므로 **실제 데스크탑 IP로 바꿉니다**.

```bash
export ACCEPT_EULA=Y
./lekiwi remote workspace --host 192.168.0.171
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
주소는 실제 데스크탑 IP로 바꿉니다. 첫 접속에서는 서버 키를 확인하고 데스크탑 계정으로 인증합니다.

```bash
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L 127.0.0.1:8080:127.0.0.1:8080 사용자명@192.168.0.171
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
01_object_physics/experiments/01_no_gravity.py
```

각 장 README는 파일을 연 뒤 `Ctrl+Shift+V`로 이미지가 포함된 미리보기를 볼 수 있습니다.
메뉴 `Terminal → New Terminal`로 편집기 아래 터미널을 엽니다.

## 4. 기본 코드를 실행하고 화면 확인

**브라우저 편집기 안의 터미널**에서 실행합니다.

```bash
lesson run 1
```

실행은 즉시 시작되지만 GPU 준비는 시간이 걸립니다. 상태를 확인합니다.

```bash
lesson status
```

`READY`가 나오면 노트북의 [공식 Isaac Sim 5.1 WebRTC 클라이언트](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/download.html)를 열고,
Server에 **같은 데스크탑 IP**를 입력해 Connect합니다. 1~3장 기본 예제는 화면의 표준 Play 버튼을 누릅니다.
브라우저는 코드와 터미널, WebRTC 클라이언트는 Isaac Sim 화면을 담당합니다.

오래 기다려도 준비되지 않거나 `FAILED`이면 `lesson logs`로 확인합니다.
출력된 데스크탑의 `data/remote/session.*/sim.log`에 전체 Isaac Sim 로그가 있습니다.

## 5. 코드 수정 → 저장 → 종료 → 재실행

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

## 7. 파일 저장 위치와 종료

- 편집한 Python: **데스크탑 저장소의 `isaacsim_basic/각장/experiments/`**. 편집기를 꺼도 남고, 코드 변경만으로 이미지 재빌드는 필요하지 않습니다.
- 교재·안내: 편집기에서는 읽기 전용입니다. Python 실습 폴더만 수정할 수 있습니다.
- 수업 기록: 데스크탑 `data/isaacsim_basic/`, LeKiwi 시연은 `data/recordings/`. 편집기의 결과 폴더에서 읽을 수 있습니다.
- 편집기 설정·실행 로그: 데스크탑 `data/web_classroom/`. Git에서 제외됩니다.
- 학습·변환 명령은 기존 데스크탑 절차를 사용합니다. 이 편집기 터미널은 실습 실행·종료·상태·로그를 연결합니다.

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
- 이번 편집기 검증에서 2~6장 전체 실습 반복, 실제 리더암 조작, 여러 학생 동시 접속은 수행하지 않았습니다.
