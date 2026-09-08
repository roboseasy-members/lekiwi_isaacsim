# Docker 배포 구조와 구현 범위

## 목표

Conda와 ROS 설치 없이, Git clone과 Docker 실행으로 LeKiwi + SO101을
조작하고 시뮬레이션에서 데이터를 수집·학습·평가한다. 실제 장비는 USB로
연결한 리더 팔이며, 제어 대상 베이스와 follower arm은 Isaac Sim 안에 있다.

## 실행 환경

- `sim`: Isaac Sim 5.1.0 내장 Python 3.11을 사용한다. 기존 물리 주행 모델과
  36개 수동 롤러를 유지한다. 생성된 USD, 하위 레이어, URDF, mesh를 이미지에
  포함한다. ROS bridge, ROS 메시지, RViz, colcon은 실행 경로에 없다.
- `lerobot`: Python 3.12, LeRobot 0.6.1, PyTorch 2.10.0/cu128,
  torchvision 0.25.0, TorchCodec 0.10.0을 사용한다. 데이터셋, Feetech,
  ACT, GR00T N1.7 의존성을 이미지 빌드 시 설치한다.
- 기본 Compose는 sim/lerobot 서비스를 제공한다. SO101 명령에서만 leader
  서비스를 추가하며, 지정한 USB 하나만 전달하고 네트워크는 끈다. 최신 관절값은
  공유 세션 파일로 전달하며 포트를 노출하지 않는다. 자세한 동작과 검증 제한은
  [SO101 teleop](so101-teleop.md)을 참고한다.
- `./lekiwi`는 Docker만 호출한다. 호스트 Python, ROS, Conda를 호출하지 않는다.
- 이미지 빌드 이후의 패키지 설치는 수행하지 않는다. 사전학습 가중치는
  별도 데이터이며 선택한 학습 방식에서 최초 다운로드·캐시가 필요할 수 있다.

이 조합은 2026-09-07 현재 PC에서 실제 이미지 빌드, 시뮬레이션 주행 및
LeRobot GPU 계산 검사를 통과했다. [검증 범위와 제한](validation-2026-09-07.md)을
참고한다. Isaac Sim 버전 업그레이드는 별도 물리 회귀검증으로 진행한다.
LeRobot의 간접 의존성을 포함한 118개 패키지 해석 결과는
`docker/requirements-lerobot.lock`에 고정했다. Decord의 알려진 잘못된 WHEEL
태그는 빌드 시 메타데이터만 정정하며, 실제 영상 디코딩을 검사한다.
시뮬레이터는 NVIDIA 이미지의 기본 패키지를 사용한다. 실제 설치 목록은
이미지의 `/opt/lekiwi/installed-packages.txt`에 기록한다. OS 패키지와 이미지 태그의
변경까지 피하려면 배포 시 검증된 이미지 digest를 고정해야 한다.

## 다음 구현 순서

1. 완료: 현재 PC의 Docker 이미지 빌드, USD 참조 검사, GUI·물리/GPU 검사.
2. 완료: SO101 통합 teleop을 사용자가 확인. 기록용 동작·관측 규격은 후속.
3. 완료: 보정 재사용·백업, 절대 관절 대응, 속도 단계, 손목 보정, 통신 watchdog.
4. 주행 차선·랜덤 물체·목표 바구니와 초기 배치 저장/재생 구현.
   [환경 실행](collection-course.md). 전방/손목 카메라 임시 장착과 시점 전환 구현.
   [카메라 설정](robot-cameras.md). 실제 TF 보정·영상 동기화·런타임 에피소드 리셋은 후속.
5. 기초 교재의 한 관절 JSON 기록·재생 구현: [5편](../isaacsim_basic/05_data_recording/README.md).
   통합 teleop의 LeRobotDataset 기록, 영상·명령 동기화, 종료 시 finalize는 후속.
6. ACT 학습 및 시뮬레이션 평가, 이후 GR00T 미세조정과 평가.
7. 환경 생성용 Script Editor 예제 제공. 통합 teleop의 비동기 시작/종료는 후속.

Script Editor에서는 이미 실행 중인 SimulationApp을 재생성하지 않는다.
현재 `keyboard_drive.py`는 독립 실행용이므로 Script Editor에 그대로 붙여넣지 않는다.

## 공통 데이터 규격 초안

- 동작: 베이스 `vx`, `vy` (m/s), `wz` (rad/s), 팔 5개 관절 목표와
  그리퍼 관절 목표 (rad). 최종 LeRobot feature 명칭은 연결 모듈 구현 시 고정.
- 관측: 카메라 RGB, 실제 관절값, 필요한 베이스 상태, 시뮬레이션 시각,
  에피소드/프레임 번호. 객체의 정답 위치는 평가 정보로 구분.
- 키보드, 리더 팔, 정책 추론이 모두 같은 명령 검증·제한 과정을 거친다.
- 관측 시점과 해당 관측에 대해 실제 적용된 동작을 대응시킨다. 기록 속도는
  시뮬레이션 시간 기준이며, 누락·지연 프레임을 정상 FPS처럼 숨기지 않는다.
- 컨테이너 연결은 명시적 프레임 번호와 시간 제한을 가진 통신으로 구현한다.
  명령이 끊기면 베이스 정지 및 팔 목표 유지. 에피소드 리셋 시 이전 명령 제거.

## 영구 데이터

`data/`를 `/data`에 연결하고 호스트 UID/GID로 실행한다. 데이터셋, 출력 모델,
리더 보정값, 다운로드·렌더링 캐시가 컨테이너 삭제 후에도 유지된다.
`src/`, CAD 원본, RViz 패키지, 로그, Git 정보, `.env`, 사용자 데이터는 Docker
빌드 컨텍스트에서 제외한다. 사용자의 기존 개발 자료는 삭제하지 않는다.

## 배포 전 확인

- 프로젝트 경로를 옮긴 fresh clone에서도 기본 자산 검사가 통과하는지 확인.
- 실제 이미지 안에서 USD의 하위 레이어·mesh·texture가 모두 해결되는지 확인.
- 현재 USD는 5개 로컬 레이어로 구성되며, 가져온 재질 정의에 Isaac 기본
  `OmniPBR.mdl` 참조가 남아 있다. 실제 화면은 기존 PreviewSurface 재질을 쓴다.
  이 셰이더는 로봇 자산 다운로드 대상이 아니며, 이미지 안의 Isaac 설치가 제공한다.
- 기본 데모가 별도 로봇 자산 다운로드 없이 뜨는지 확인.
- GUI 종료/재실행, 캡처 쓰기 권한, 중복 실행 방지를 확인.
- `test-physics`, `check-ml`을 호환 GPU에서 통과시킨다.
- 설치 목록·이미지 digest·시험 결과를 릴리스에 기록한다.
- 자산 출처는 `isaac_sim/assets/lekiwi_soarm/SOURCE.md`에 있다. 기존 파일에는
  재배포 라이선스 확인 자료가 완결되어 있지 않으므로 공개 이미지 배포 전에
  몸체·휠·팔 mesh의 재배포 조건을 확인한다. 이 문서는 권리를 새로 부여하지 않는다.

## 공식 참고 자료

- [Isaac Sim 5.1 Docker](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/install_container.html)
- [LeRobot 0.6.1 의존성 정의](https://github.com/huggingface/lerobot/blob/v0.6.1/pyproject.toml)
- [TorchCodec 버전 호환표](https://github.com/pytorch/torchcodec#compatibility-with-torch-versions)
- [LeRobot 데이터셋](https://huggingface.co/docs/lerobot/main/lerobot-dataset-v3)
