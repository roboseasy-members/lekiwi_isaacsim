# 0장 · 공식 자료와 확인 범위

문서 확인일: 2026-09-14. 수업 런타임은 Isaac Sim 5.1.0, 영상 클라이언트는 공식 1.1.5입니다.

## 공식 자료

- [Tailscale Linux 설치](https://tailscale.com/download/linux): 양쪽 Ubuntu PC의 공식 설치 경로.
- [Tailscale 시작 안내](https://tailscale.com/docs/how-to/quickstart): 계정 생성과 첫 번째·두 번째 기기 등록 흐름.
- [지원하는 로그인 방식](https://tailscale.com/docs/integrations/identity): Google 등 기존 계정 인증과 별도 Tailscale 비밀번호가 없는 이유.
- [Linux에서 인증·연결 확인](https://tailscale.com/docs/install/linux): 터미널 인증 링크, 기기 목록과 상태·주소 확인.
- [Tailscale CLI](https://tailscale.com/docs/reference/tailscale-cli): `up`, `status`, `ip -4`, `ping`, `logout`의 사용과 `down`의 차이.
- [Tailscale 계정과 네트워크](https://tailscale.com/docs/concepts/tailscale-identity): 계정·네트워크에 기기를 연결하는 방식.
- [직접 연결과 중계 연결](https://tailscale.com/docs/reference/device-connectivity): 연결 경로에 따른 지연 점검.
- [관리 목록에서 기기 제거](https://tailscale.com/docs/features/access-control/device-management/how-to/remove): 반납한 데스크탑의 등록 제거.
- [code-server SSH 접속](https://coder.com/docs/code-server/guide#port-forwarding-via-ssh): SSH 인증과 포트 전달을 사용하고 편집기의 별도 비밀번호 입력을 생략하는 구성.
- [NVIDIA의 Tailscale 설정 예제](https://build.nvidia.com/spark/tailscale/instructions): 서버·클라이언트 연결과 일반 SSH 접속 참고. DGX Spark용 예제 중 네트워크 준비 흐름을 참고했습니다.
- [Isaac Sim 5.1 다운로드](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/download.html): 공식 WebRTC Streaming Client 선택.
- [Isaac Sim 5.1 Livestream](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/manual_livestream_clients.html): 헤드리스 송출, 접속 주소, TCP 49100·UDP 47998.
- [Isaac Sim 5.1 컨테이너 최초 실행](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/install_container.html#container-deployment): 최초 셰이더 캐시 준비로 수 분 소요될 수 있으며, 준비 완료 후 영상 클라이언트를 연결하는 순서.

계정 구성은 학생별 독립 네트워크에 사용자 1명과 배정된 두 PC를 등록하는 방식입니다.
수업의 요금제·이용 조건은 강사가 [현재 요금제](https://tailscale.com/pricing)를 기준으로 확인합니다.
특정 사용자 수나 무료 조건을 설치 성공의 기준으로 사용하지 않습니다.

## 프로젝트에 적용한 범위

`test` 브랜치의 데스크탑·노트북 구분과 관찰 결과 제출 흐름을 참고했습니다.
0장은 현재 `develop`의 브라우저 편집기와 `lesson` 명령으로 진행합니다.
화면 확인에는 기존 [1장 중력·충돌 예제](../01_object_physics/experiments/03_gravity_collision.py)를 사용합니다.
0장은 준비 교재이며 시뮬레이션 장 번호 1~6은 그대로 사용합니다.

브라우저의 기존 교재 마운트가 `00_env_setting`도 읽기 전용으로 제공합니다.
코드·교재 목차와 명령 연결 검사는 실제 Tailscale 접속·영상 수신 성공을 대신하지 않습니다.
Tailscale을 경유한 영상·Play/Stop, 실제 수업망과 15쌍 동시 사용은 학생 기록과 리허설에서 별도로 확인합니다.
노션 ZIP에는 이 장의 교재·기록지·출처 HTML과 본문에 사용한 이미지를 포함합니다.

## 2026-09-14 · 가입·로그인 화면 보완

0장을 따라가는 사용자가 가입·로그인 화면의 스크린샷이 없어 선택할 버튼을 찾기 어렵다는 점을 지적했습니다.
공식 공개 페이지를 계정에 로그인하지 않은 별도 브라우저에서 900×760 크기로 직접 캡처했습니다.
개인 계정·비밀번호·기기 인증 링크는 입력하거나 촬영하지 않았습니다. 아래 사진은 가입 완료나 두 PC의 연결 성공을 검증한 사진과 구분합니다.

원본 PNG는 `images/screenshots/`에 보관합니다. `images/annotations.json`에 표시 좌표를 기록하고,
기존 `01_object_physics/images/build_annotations.py`로 원본을 그대로 포함한 SVG와 빨간 테두리를 만들었습니다.
본문용 PNG와 Notion ZIP은 `export_lessons.py`로 생성합니다. 원본의 버튼·문구·상태를 합성하거나 바꾸지 않았습니다.

| 원본 | 출처 | 확인할 부분 |
|---|---|---|
| `images/screenshots/02-tailscale-sign-up.png` | [공식 가입 페이지](https://login.tailscale.com/start) | Google 계정을 사용할 때 선택하는 가입 버튼 |
| `images/screenshots/03-tailscale-sign-in.png` | [공식 로그인 페이지](https://login.tailscale.com/login) | 기존 Google 계정으로 다시 로그인하는 버튼 |

다른 운영체제나 오래된 관리 화면을 이번 두 PC의 연결 성공 화면으로 사용하지 않습니다.
기기 인증 링크·QR 코드·비밀번호가 보이는 화면은 촬영에서 제외하고, 기기 이름·주소·연결 상태처럼 확인에 필요한 영역을 사용합니다.

## 2026-09-14 · 두 PC의 Machines 목록 캡처

사용자가 양쪽 PC의 인증을 마친 뒤 열어 둔 [Machines 페이지](https://login.tailscale.com/admin/machines)를 직접 확인했습니다.
원본 `images/screenshots/04-tailscale-machines.png`는 실제 브라우저의 기기 목록 영역을 1350×365 크기로 촬영한 화면입니다.
브라우저 주소창과 다른 창은 촬영 범위에서 제외했으며, 기기 목록의 이름·주소·상태는 변경하지 않았습니다.
가입·로그인 사진과 같은 SVG 주석 방식으로 이름·주소·Connected 열에 빨간 테두리를 추가했습니다.

| 실습 역할 | 기기 이름 | Tailscale IPv4 | 촬영 시 표시 |
|---|---|---|---|
| 서버 역할의 서브 노트북 | `roboseasy` | `100.66.115.54` | Connected |
| 화면을 볼 메인 노트북 | `ysj` | `100.76.197.70` | Connected |

이 화면은 두 기기의 등록·온라인 상태를 보여줍니다. 같은 날 메인 노트북의 Tailscale ping도 서버로 3회 응답했으며,
지연은 22·19·19 ms, 직접 연결 경로는 회사 LAN 주소였습니다.
이 캡처를 다른 인터넷 회선에서의 접속, Isaac Sim 영상·조작 또는 15쌍 동시 사용의 검증 사진으로 사용하지 않습니다.
최초 기기 인증 화면과 터미널의 주소·ping 결과 화면은 이번 이미지에 포함하지 않았습니다.

## 2026-09-14 · 첫 실습의 STARTING 대기 확인

서버의 새 `test_ws/lekiwi_classroom` 폴더에서 `lesson run --experiment 3`을 실행한 뒤 준비 상태를 추적했습니다.
Kit 로그에 `Waiting for RtPso async group async compilation`이 5초 간격으로 기록되었고,
약 2분 후 `STUDENT_SCRIPT ready file=03_gravity_collision.py`와 실제 `lesson status`의 READY를 확인했습니다.
실습을 재시작하거나 런타임 코드를 변경하지 않고 준비가 완료됐습니다. 이 시간은 해당 RTX 3070 Laptop 실습 장비에서 관찰한 값이며, 모든 장비의 고정 대기 시간이 아닙니다.

확인 로그는 서버 수업 폴더의 `data/remote/session.9p7khedr/sim.log`와
`data/logs/sim/Kit/Isaac-Sim Python/5.1/kit_20260914_055305.log`입니다.
이 확인은 실습 준비 완료까지이며, 영상 표시·Play/Stop은 다음 단계에서 별도로 확인합니다.

## 2026-09-14 · AppRun의 옵션 전달 시 경로 오류 보완

본 노트북에 다운로드한 WebRTC Streaming Client 1.1.5의 `squashfs-root/AppRun`을 읽어 확인했습니다.
스크립트는 `APPDIR`이 없으면 첫 번째 인자(`$1`)를 파일 이름으로 사용해 폴더를 찾습니다.
이 때문에 `--no-sandbox`를 전달하면 폴더 경로가 비어 `/isaacsim-webrtc-streaming-client`를 실행하려다가 실패했습니다.

원본 실행 스크립트와 임시 검사용 실행 파일을 사용해 오류를 재현했습니다.
`APPDIR="$PWD/squashfs-root"`를 지정한 명령은 옵션 유무와 공백이 포함된 경로에서 모두 정확한 실행 파일·인자를 전달했습니다.
검사한 원본 AppRun의 SHA-256은 `b3a89e0d7387ce6720259271a5939eeb30f13c1db12d6d60378ed09a60bafbf9`입니다.
공식 배포 파일과 시스템의 sandbox 권한은 수정하지 않았습니다. 이 검사는 실행 경로 전달까지이며, 실제 영상 표시는 실습에서 확인합니다.

[교재로 돌아가기](README.md)
