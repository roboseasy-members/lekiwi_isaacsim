# Docker 실행 검증 — 2026-09-07

## 환경과 범위

Linux x86_64, Docker 29.8, Compose 5.5.1, NVIDIA 드라이버 580.173.02,
RTX 5060 Laptop GPU (8 GiB)에서 검사했다. 호스트 Conda/ROS를 사용하지 않았다.
실제 로봇이나 리더 팔은 연결·조작하지 않았다. 공개 이미지 배포는 하지 않았다.

## 확인 결과

- 시뮬레이션 이미지 로컬 빌드와 `./lekiwi validate` 통과.
- `ACCEPT_EULA=Y ./lekiwi validate-usd` 통과: 로컬 USD 레이어 5개,
  rigid body 48개, joint 45개, collider 57개, 수동 롤러 36개, 팔 visual 17개.
  외부 자산 참조 1개는 이미지 내장 `OmniPBR.mdl`이며 추가 로봇 다운로드는 없다.
- `ACCEPT_EULA=Y ./lekiwi test-physics` 통과: 전진 0.22832 m,
  왼쪽 평행이동 0.23298 m, 반시계 회전 0.78453 rad. 옆 방향 오차는
  각각 0.00510 m, 0.00035 m였다.
- GUI에서 `LEKIWI_DRIVE result=READY`, 키 입력에 따른 명령 및 위치 변화,
  화면 캡처를 확인했다. 로봇 몸체·휠·팔 메시가 표시된다.
  캡처는 `data/captures/lekiwi_viewport.png`이며 로그인 사용자 소유로 저장됐다.
  점검용 GUI는 프로젝트 전용 `./lekiwi stop`으로 종료했다.
- 존재하지 않는 USD 경로를 주입한 실제 컨테이너 검사는 FAIL을 출력하고
  종료 코드 1을 반환했다. 실패가 성공으로 보고되지 않는 것을 확인했다.
- 배포 자동 테스트 22개, Bash 문법 검사, Compose 설정 검사, `git diff --check` 통과.
- LeRobot 이미지 빌드와 `pip check` 통과. LeRobot 0.6.1,
  PyTorch 2.10.0+cu128, torchvision 0.25.0+cu128, TorchCodec 0.10.0 조합이다.
  ACT/GR00T/데이터셋/리더 모듈 import, Decord·TorchCodec 합성 영상 디코딩,
  실제 CUDA 텐서 계산이 일반 사용자 권한 컨테이너에서 통과했다.

## 점검 중 수정

- NVIDIA 이미지의 `/isaac-sim` 접근 권한(0750, 그룹 1234)에 맞춰
  보조 그룹을 추가했다. 실행 UID/GID는 계속 호스트 사용자 값이다.
- Kit portable 모드의 설치 경로 기준 cache/data/log 디렉터리를 호스트의
  쓰기 가능한 `data/` 하위 디렉터리에 연결했다.
- 호스트 UID가 이미지의 `/etc/passwd`에 없어 PyTorch import가 실패하는
  문제를 재현했다. LeRobot 이미지에 USER/LOGNAME과 쓰기 가능한
  TORCHINDUCTOR_CACHE_DIR을 명시했다. root 실행으로 우회하지 않는다.
- USD 의존성 검사에서 Isaac 설치가 제공하는 정확한 기본 셰이더 경로를 허용했다.
  그 외 번들 밖 로봇 자산 참조는 계속 오류다.
- Isaac 종료 과정에서 검사 실패 후에도 프로세스가 0으로 종료하는 사례를
  재현했다. 이제 검사 명령은 종료 코드와 명시적인 PASS 표식을 모두 요구한다.
- Decord 0.6.0 배포 휠의 잘못된 내부 cp36 태그를 원래 배포 파일명의 py3-none
  태그로 정정한다. 설치된 WHEEL과 RECORD의 해당 체크섬만 갱신하며
  라이브러리 코드는 변경하지 않는다. [원본 이슈](https://github.com/dmlc/decord/issues/356).
  Python 3.12에서
  합성 영상 5프레임 디코딩을 별도로 확인했다. 빌드와 `check-ml`에서도
  Decord/TorchCodec 영상 디코딩 검사를 실행한다.

## 알려진 제한

- 기존 USD의 비시각적 `gripper_frame_link`에 존재하지 않는 visual prim을
  가리키는 경고가 남아 있다. 파일 누락과는 구분되며 팔 visual 17개 검사 및
  실제 화면 검사는 통과했다. 기존 모델의 경고 정리는 별도 작업이다.
- 리더 팔 연결, 환경/객체 편집, 데이터 수집, ACT/GR00T 실제 학습·추론,
  Script Editor 사용 흐름은 이번 검증 대상이 아니며 아직 후속 구현이다.
- GPU 실행 성공이 모든 모델의 학습 메모리 충족을 의미하지 않는다.
- 이 PC의 로컬 빌드 검증이다. 공개 배포 전에는 자산 재배포 라이선스 확인,
  검증 이미지 digest 고정, 다른 PC/fresh clone 시험이 필요하다.

## 로컬 재확인 명령

Docker에 sudo가 필요한 이 PC에서는 각 명령 앞에 `LEKIWI_DOCKER_SUDO=1`을 붙인다.

```bash
./lekiwi validate
ACCEPT_EULA=Y ./lekiwi validate-usd
ACCEPT_EULA=Y ./lekiwi test-physics
./lekiwi check-ml
```

원시 점검 로그는 이 PC의 `/tmp/lekiwi-*-20260907.log`, 시뮬레이터의
검사 로그는 `data/logs/sim/check.*.log`에 있다. `/tmp` 파일은 배포 자산이 아니다.
