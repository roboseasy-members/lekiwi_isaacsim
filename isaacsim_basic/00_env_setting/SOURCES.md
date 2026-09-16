# 0장 · 출처와 검증 범위

이 장은 Ubuntu NVIDIA GPU 노트북 한 대에서 진행하는 수업입니다.

- [설치 도구와 지원 범위](../../docs/student-setup.md): 이 저장소의 드라이버·Docker 준비 정책.
- [실제 실행기](../../lekiwi): 로컬 GUI, X11 인증, 결과 저장 위치.
- [VS Code 공식 Linux 설치](https://code.visualstudio.com/docs/setup/linux): Snap·Debian/Ubuntu 패키지 설치 안내.
- [설치 흐름 구현](../../tools/host_setup/main.py): `install`에서 호스트 준비 → `setup all` 이미지 빌드 → 자동 검사를 실행하며, 재부팅 뒤 같은 명령으로 이어갑니다.
- [Ubuntu Secure Boot와 MOK](https://documentation.ubuntu.com/security/security-features/platform-protections/secure-boot/): 드라이버 서명 검사와 키 등록의 역할.
- [Ubuntu 24.04 mokutil 명령](https://manpages.ubuntu.com/manpages/noble/man1/mokutil.1.html): `--sb-state`, `--test-key`, `--import`, `--list-new`의 의미.
- [Ubuntu 공식 MOK 등록 화면 순서](https://iso.qa.ubuntu.com/qatracker/testcases/1771/revisions/2031/info): `Enroll MOK → Continue → Yes → 비밀번호 → Reboot`. 원문의 OS 설치 절차 전체가 아니라 MOK 등록 단계만 참고합니다.
- [Isaac Sim 5.1 컨테이너 설치](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/install_container.html).
- [Isaac Sim 5.1 UI 구성](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/gui/reference_user_interface.html): Viewport·Stage·도구막대와 Play/Stop의 역할.
- `images/01-overview.png`: [1장의 실제 원본](../01_object_physics/images/screenshots/17-code-first.png)을 재사용했습니다. 파란 `PracticeCube` 한 개가 공중에 있는 실행 전 화면이며, 이번 노트북에서 새로 촬영한 사진은 아닙니다. 원본은 `images/screenshots/01-overview.png`에 바이트 변경 없이 보관합니다.

## 2026-09-15 전환

두 PC의 Tailscale·SSH·WebRTC 설정을 수업 절차에서 제거했습니다. 이전 원격 최종본은 `feature/remote_classroom`의 `b5dd9e6`입니다.
이번 변경은 로컬 실행 경로·교재·명령 검사를 대상으로 합니다. RTX 3070 대여 노트북에서 0장의 Play/Stop과 실제 리더 조작은 강사 리허설에서 확인합니다.

## 학생 직접 설치 안내

VS Code가 없는 상태부터 학생이 직접 설치하고, GPU·Docker 준비와 이미지 빌드·검사를 진행하도록 0장을 보완했습니다.
재부팅 후 이어가기, 설치 도구 종료 후 Docker 권한 설정, check·verification·GUI 관찰의 완료 기준을 구분합니다.
문서·명령 구문·설치 흐름 대응을 검사하며, 새 노트북 설치·15대 동시 다운로드 시간은 실제 수업 환경에서 확인해야 합니다.

## Secure Boot·MOK 등록 안내 보완

Ubuntu 24.04 수업용 노트북에서 사용자가 제공한 로그를 바탕으로 3.3절에 진단·등록·재부팅·설치 재개 절차를 추가했습니다.
당시 커널은 `6.17.0-35-generic`, DKMS 결과는 해당 커널용 `nvidia/580.178.04: installed`였지만,
`nvidia-smi`는 드라이버와 통신하지 못했고 Secure Boot는 켜져 있었으며 MOK 키는 미등록 상태였습니다.
이 로그는 **등록 전 상태의 확인 근거**입니다. 후속 사용자 로그에서는 RTX 4060과 드라이버 `580.178.04`가 인식돼 Docker·Container Toolkit 설치와 이미지 빌드로 진행했습니다.
이는 GPU 인식 확인이며, 전체 설치·렌더링 검사를 통과했다는 뜻은 아닙니다.
문서의 명령 구문·링크·노션 ZIP을 검사하며, 이 문서 보완 작업에서 호스트의 키·드라이버·부팅 설정은 변경하지 않습니다.

## 단일 큐브와 뷰포트 안내 보완

학생 리허설에서 실행 화면은 파란 큐브 한 개인데 교재 사진은 큐브 세 개여서 혼동이 발생했고, 뷰포트 위치도 찾기 어려웠습니다.
[실험 번호 매핑](../experiments.py)과 [3번 실험](../01_object_physics/experiments/03_gravity_collision.py)을 확인해 시작 장면을 명시했습니다.
큰 뷰포트 테두리와 작은 Play 테두리만 표시하고, 빈 바닥을 클릭하는 위치와 버튼 모양·도움말을 설명했습니다.
원본은 변경하지 않고 기존 [SVG 표시 생성기](../01_object_physics/images/build_annotations.py)에 `images/annotations.json`을 전달해 테두리·하단 설명을 생성합니다.
재생성: `python3 isaacsim_basic/01_object_physics/images/build_annotations.py isaacsim_basic/00_env_setting/images` 후
`/usr/bin/python3 isaacsim_basic/export_lessons.py isaacsim_basic/00_env_setting`.
