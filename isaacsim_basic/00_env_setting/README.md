# 0장 · 환경 설정 — 노트북 한 대로 수업 준비하기

**배정받은 Ubuntu NVIDIA GPU 노트북 한 대에서 코드 편집, Isaac Sim 화면, 리더암 조작, 데이터 수집과 학습을 진행합니다.**
리더암 USB도 이 노트북에 연결합니다. 장비 연결과 보정은 4장 또는 6장의 리더 실습에서 합니다.

처음에는 **이 README를 위에서 아래로** 따라갑니다. 저장소 맨 앞의 [README](../../README.md)는 전체 기능을 찾아보는 참고 문서입니다.
0장의 화면·Play/Stop 확인을 마친 뒤 1장으로 넘어갑니다.

| 준비물 | 용도 |
|---|---|
| Ubuntu 22.04/24.04 x86_64 NVIDIA GPU 노트북과 전원 어댑터 | 실습 전체 실행. 수업 중 전원 연결 |
| 인터넷 | 저장소·Docker 이미지·필요한 모델 다운로드, 선택한 데이터셋 업로드 |
| 노트북에 설치된 VS Code 또는 텍스트 편집기 | 교재 읽기와 Python 파일 수정 |
| SO101 리더암·USB·전원 | 4·6장에서 같은 노트북에 연결 |

대여 RTX 3070 노트북도 아래 실행 검사로 준비 상태를 확인합니다. GPU 이름만으로 모든 실습과 학습의 성능을 보장하지 않습니다.
Tailscale, AnyDesk, SSH 터널, 브라우저 편집기, WebRTC 클라이언트 설치 단계는 이번 수업에 없습니다.

## 1. 교재 받기

노트북의 Ubuntu 바탕화면에서 `Ctrl+Alt+T`로 터미널을 엽니다. Git이 없다면 `sudo apt update`와 `sudo apt install git`으로 준비합니다.
강사에게 저장소 접근 권한을 받은 뒤, 교재를 둘 폴더에서 실행합니다. 기존 폴더를 덮어쓰거나 지우지 않습니다.

```bash
git clone --branch develop --single-branch https://github.com/SJun99/lekiwi_isaacsim.git lekiwi_classroom
cd lekiwi_classroom
git branch --show-current
pwd
ls lekiwi
```

브랜치는 `develop`, 마지막 출력은 `lekiwi`인지 확인합니다.
**이후 `./lekiwi` 명령은 항상 이 저장소 최상위 폴더에서 실행합니다.**
`isaacsim_basic` 폴더 안에서 실행하면 `No such file or directory`가 납니다.
새 터미널을 열었다면 방금 `pwd`에 나온 실제 폴더로 `cd`한 뒤 실행하세요.

## 2. GPU·Docker 실행 환경 준비

먼저 읽기 전용 검사로 현재 상태를 확인합니다.

```bash
./lekiwi install --check
```

`check=PASS`는 준비 절차를 진행할 수 있다는 뜻입니다. Isaac Sim 창이 실행됐다는 뜻은 아닙니다.
강사가 수업 이미지를 이미 준비했는지 확인합니다.

- **처음 설치하는 노트북:** [학생 PC 설치 안내](../../docs/student-setup.md)의 ‘처음 실행’부터 설치·필요한 재부팅·검증을 마친 뒤 이 장으로 돌아옵니다.
- **설치를 마친 노트북:** 아래 라이선스·Docker 권한을 설정하고 `./lekiwi install --verify`로 기존 이미지의 GPU·두 카메라·짧은 기록 검사를 실행합니다.
- **기존 수업 코드에서 업데이트한 노트북:** 작업을 보관하고 [업데이트 절차](../../README.md#업데이트와-브랜치)에 따라 이미지를 갱신한 뒤 검사합니다.

[NVIDIA 라이선스](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-software-license-agreement/)를 읽고 동의한 경우, 실습할 터미널에 설정합니다.

```bash
export ACCEPT_EULA=Y
export LEKIWI_DISPLAY_MODE=local
docker info
```

`docker info`에 권한 오류가 나지만 `sudo docker info`는 성공하면 같은 터미널에서 다음을 한 번 설정합니다.

```bash
export LEKIWI_DOCKER_SUDO=1
```

`sudo` 비밀번호는 **지금 사용하는 노트북의 Ubuntu 로그인 비밀번호**입니다. 입력 중 문자가 보이지 않아도 입력되고 있습니다.
프로젝트 전체를 `sudo ./lekiwi ...`로 실행하지 않습니다. 새 터미널에서는 위 `export` 설정을 다시 적용합니다.

준비된 이미지로 검사합니다. USB 리더를 열지 않는 검사입니다.

```bash
./lekiwi install --verify
```

**완료 기준:** `LEKIWI_INSTALL verification=PASS`입니다. 실패하면 마지막 오류와 로그 경로를 강사에게 보여줍니다.
여기까지 성공했다면 매번 설치하거나 이미지를 다시 빌드할 필요는 없습니다.
호스트에 Isaac Sim·LeRobot·Conda·CUDA Toolkit을 따로 설치하는 수업이 아닙니다. 실습 의존성은 Docker 이미지에 있습니다.

## 3. 같은 노트북에서 교재와 코드 열기

노트북에 설치된 **VS Code**의 `File > Open Folder`에서 1절의 `lekiwi_classroom` 폴더를 엽니다.
VS Code가 없는 대여 장비라면 강사에게 편집기 준비를 요청합니다. 다른 텍스트 편집기도 사용할 수 있습니다.

1. 왼쪽 탐색기에서 `isaacsim_basic > 00_env_setting > README.md`를 엽니다.
2. `Ctrl+Shift+V`를 눌러 Markdown 미리보기를 엽니다. 이 화면에서 교재를 읽습니다.
3. `Terminal > New Terminal`로 터미널을 열고 `pwd`와 `ls lekiwi`로 저장소 최상위 폴더인지 확인합니다.
4. 새 터미널이면 2절의 `export` 설정을 적용합니다. Ubuntu 터미널을 계속 사용해도 됩니다.

편집기 비밀번호나 접속 주소를 설정하지 않습니다. 화면 위쪽에 `coder@...:/workspace/...`가 보이는 이전 브라우저 편집기 대신 **지금 노트북의 로컬 편집기**를 사용합니다.
Python은 해당 장 마지막에서 수정합니다. 먼저 아래 화면 실행을 확인합니다.

## 4. Isaac Sim 화면과 Play/Stop 확인

저장소 최상위 폴더의 터미널에서 실행합니다.

```bash
./lekiwi basic --experiment 3
```

**같은 노트북에 Isaac Sim 창이 직접 열립니다.** 처음에는 캐시·셰이더 준비로 시간이 걸릴 수 있습니다.
터미널을 유지하며 기다리고, 같은 명령을 여러 번 실행하지 않습니다.
바닥과 파란 큐브가 나타나고 마우스 조작이 가능해지면 아래를 확인합니다.

![Isaac Sim 기본 도구의 위치](images/01-overview.png)

사진은 1장 제작 당시의 실제 화면입니다. 빨간 표시로 Viewport·Stage·Property·Play/Stop 위치를 찾습니다.
현재 확인용 장면의 물체 배치는 사진과 다를 수 있습니다.

1. Viewport를 클릭합니다.
2. 왼쪽 **Play(삼각형)**를 눌러 큐브가 떨어지고 바닥 위에서 멈추는지 봅니다.
3. **Stop(사각형)**을 눌러 처음 위치로 돌아오는지 확인합니다.
4. Play를 다시 눌러 같은 동작이 되는지 확인하고 Stop합니다.
5. [기록지](worksheet.md)에 결과를 적고 화면을 캡처해 강사에게 제출합니다.

**완료 기준:** 창이 열리고, 큐브 낙하·바닥 충돌·Stop 후 복원을 직접 확인했습니다.
로그에 준비됐다는 문구가 나온 것만으로 완료 표시하지 않습니다.

### 창이 안 뜨거나 느릴 때

- 터미널에 명확한 오류가 있으면 그 오류부터 확인합니다. 프로그램을 중복 실행하지 않습니다.
- `DISPLAY`·X11·XAUTHORITY 오류이면 Ubuntu 그래픽 화면 안에서 연 로컬 터미널인지 확인합니다. 임의의 주소를 넣거나 `xhost +`로 풀지 말고 강사에게 화면과 오류를 보여줍니다.
- CUDA·메모리 오류이면 다른 GPU 작업을 정상 종료하고 강사와 로그를 확인합니다. 드라이버 설치를 반복하지 않습니다.
- 화면이 열렸지만 물체가 안 움직이면 Play 상태와 Viewport 선택부터 확인합니다.

## 5. 종료하고 1장 시작하기

Isaac Sim 창을 닫습니다. 터미널 프롬프트가 돌아온 뒤 확인합니다.

```bash
./lekiwi status
```

실행 중인 실습 컨테이너가 없는지 확인하고 [1장 · 객체와 물리](../01_object_physics/README.md)로 넘어갑니다.
1장은 빈 화면에서 마우스로 물체를 만드는 것부터 시작합니다.

수업 중에는 노트북의 인터넷 주소를 입력하거나 다른 컴퓨터에 접속하지 않습니다.
결과는 저장소의 `data/`에 남습니다. Isaac Sim 안의 `/data`와 노트북의 `data/`는 같은 저장 공간입니다.
전체 수업이 끝나면 결과와 개인 보정 파일을 보관하고 프로그램을 정상 종료합니다. 공용 노트북 브라우저의 개인 계정도 로그아웃합니다.
