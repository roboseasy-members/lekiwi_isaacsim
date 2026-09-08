# 4편 출처·검증

대상: Isaac Sim 5.1.0 / LeRobot 0.6.1 Docker. 문서 확인일: 2026-09-07.

- 프로젝트 `lekiwi`, `tools/so101_leader.py`: 실제 실행·보정·기존 파일 선택·토크 확인 순서.
- 프로젝트 `isaac_sim/keyboard_drive.py`, `drive_controls.py`, `teleop_bridge.py`: 키보드 조작, 절대각 대응, 속도 단계, 제한·재활성화.
- [LeRobot 0.6.1 SOLeader 구현](https://github.com/huggingface/lerobot/blob/v0.6.1/src/lerobot/teleoperators/so_leader/so_leader.py): 연결·보정·위치 읽기 API.
- [NVIDIA Articulation Controller](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/robot_simulation/articulation_controller.html): 관절 위치·속도·힘 제어와 rad 단위.

## 제작 시 실제 확인

- 실제 리더 USB를 열지 않고 sim 모드로 촬영했습니다.
- 팔 기본 자세 유지 표시, W 전진 명령, 이동키 해제 후 STOP, 1/2 속도 단계 변경, T 추적 시점을 확인했습니다.
- Space가 기본 Isaac 재생 단축키와 함께 작동해 Pause로 바뀌는 경우를 확인하고 교재에 재개 확인 절차를 넣었습니다.
- GUI의 문자·숫자 입력 중 전역 조작키가 반응하는 경우를 확인했습니다. 3편의 속성 편집 절차에 Pause를 선행하도록 명시했습니다.
- 원본 화면 4장은 `images/screenshots/`, 강조 위치는 `images/annotations.json`입니다.
  원본 PNG에 벡터 사각형·하단 설명을 더한 뒤 문서용 PNG를 렌더링했습니다.
- 이번 제작에서는 실제 리더 연결·보정·ACTIVE 조작·실물 방향·영점·집기 성공을 새로 검증하지 않았습니다.
  해당 절은 실제 구현과 기존 프로젝트 안내를 근거로 작성한 교육생 실습 절차입니다.

## 자동 검사 결과

- 전체 USD·기존 회귀 검사: 193 passed, 1 skipped.
- Docker `test-arm`: 6개 관절, 절대각·지연·재활성화 검사 PASS. 개별 추종 최대 오차 약 0.0018 rad.
- Docker `test-physics`: 전진 0.22832 m, 좌측 0.23298 m, 반시계 회전 0.78453 rad 및 최종 PASS.
- 자동 입력 검사는 실제 리더의 보정·방향 검증을 대신하지 않습니다.
