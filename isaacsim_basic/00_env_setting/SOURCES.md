# 0장 · 공식 자료와 확인 범위

문서 확인일: 2026-09-13. 수업 런타임은 Isaac Sim 5.1.0, 영상 클라이언트는 공식 1.1.5입니다.

## 공식 자료

- [Tailscale Linux 설치](https://tailscale.com/download/linux): 양쪽 Ubuntu PC의 공식 설치 경로.
- [Tailscale CLI](https://tailscale.com/docs/reference/tailscale-cli): `up`, `status`, `ip -4`, `ping`, `logout`의 사용과 `down`의 차이.
- [Tailscale 계정과 네트워크](https://tailscale.com/docs/concepts/tailscale-identity): 계정·네트워크에 기기를 연결하는 방식.
- [직접 연결과 중계 연결](https://tailscale.com/docs/reference/device-connectivity): 연결 경로에 따른 지연 점검.
- [관리 목록에서 기기 제거](https://tailscale.com/docs/features/access-control/device-management/how-to/remove): 반납한 데스크탑의 등록 제거.
- [NVIDIA의 Tailscale 설정 예제](https://build.nvidia.com/spark/tailscale/instructions): 서버·클라이언트 연결과 일반 SSH 접속 참고. DGX Spark용 예제 중 네트워크 준비 흐름을 참고했습니다.
- [Isaac Sim 5.1 다운로드](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/download.html): 공식 WebRTC Streaming Client 선택.
- [Isaac Sim 5.1 Livestream](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/manual_livestream_clients.html): 헤드리스 송출, 접속 주소, TCP 49100·UDP 47998.

계정 구성은 학생별 독립 네트워크에 사용자 1명과 배정된 두 PC를 등록하는 방식입니다.
수업의 요금제·이용 조건은 강사가 [현재 요금제](https://tailscale.com/pricing)를 기준으로 확인합니다.
특정 사용자 수나 무료 조건을 설치 성공의 기준으로 사용하지 않습니다.

## 프로젝트에 적용한 범위

`test` 브랜치의 데스크탑·노트북 구분과 관찰 결과 제출 흐름을 참고했습니다.
0장은 현재 `feature/remote_classroom`의 브라우저 편집기와 `lesson` 명령으로 진행합니다.
화면 확인에는 기존 [1장 중력·충돌 예제](../01_object_physics/experiments/03_gravity_collision.py)를 사용합니다.
0장은 준비 교재이며 시뮬레이션 장 번호 1~6은 그대로 사용합니다.

브라우저의 기존 교재 마운트가 `00_env_setting`도 읽기 전용으로 제공합니다.
코드·교재 목차와 명령 연결 검사는 실제 Tailscale 접속·영상 수신 성공을 대신하지 않습니다.
Tailscale을 경유한 영상·Play/Stop, 실제 수업망과 15쌍 동시 사용은 학생 기록과 리허설에서 별도로 확인합니다.
새로 촬영한 검증 화면은 포함하지 않았습니다. 노션 ZIP에는 이 장의 교재·기록지·출처 HTML을 포함합니다.

[교재로 돌아가기](README.md)
