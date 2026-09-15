# 0장 · 출처와 검증 범위

이 장은 Ubuntu NVIDIA GPU 노트북 한 대에서 진행하는 수업입니다.

- [설치 도구와 지원 범위](../../docs/student-setup.md): 이 저장소의 드라이버·Docker 준비 정책.
- [실제 실행기](../../lekiwi): 로컬 GUI, X11 인증, 결과 저장 위치.
- [VS Code 공식 Linux 설치](https://code.visualstudio.com/docs/setup/linux): Snap·Debian/Ubuntu 패키지 설치 안내.
- [설치 흐름 구현](../../tools/host_setup/main.py): `install`에서 호스트 준비 → `setup all` 이미지 빌드 → 자동 검사를 실행하며, 재부팅 뒤 같은 명령으로 이어갑니다.
- [Isaac Sim 5.1 컨테이너 설치](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/install_container.html).
- `images/01-overview.png`: [1장](../01_object_physics/SOURCES.md)의 실제 화면과 빨간 도구 위치 표시를 그대로 재사용했습니다. 이번 노트북 리허설을 새로 촬영한 사진은 아닙니다.

## 2026-09-15 전환

두 PC의 Tailscale·SSH·WebRTC 설정을 수업 절차에서 제거했습니다. 이전 원격 최종본은 `feature/remote_classroom`의 `b5dd9e6`입니다.
이번 변경은 로컬 실행 경로·교재·명령 검사를 대상으로 합니다. RTX 3070 대여 노트북에서 0장의 Play/Stop과 실제 리더 조작은 강사 리허설에서 확인합니다.

## 학생 직접 설치 안내

VS Code가 없는 상태부터 학생이 직접 설치하고, GPU·Docker 준비와 이미지 빌드·검사를 진행하도록 0장을 보완했습니다.
재부팅 후 이어가기, 설치 도구 종료 후 Docker 권한 설정, check·verification·GUI 관찰의 완료 기준을 구분합니다.
문서·명령 구문·설치 흐름 대응을 검사하며, 새 노트북 설치·15대 동시 다운로드 시간은 실제 수업 환경에서 확인해야 합니다.
