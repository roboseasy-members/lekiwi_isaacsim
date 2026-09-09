# 4편 출처·검증

대상: Isaac Sim 5.1.0 / LeRobot 0.6.1 Docker. 문서 확인일: 2026-09-07.

- 프로젝트 `lekiwi`, `tools/so101_leader.py`: 실제 실행·보정·기존 파일 선택·토크 확인 순서.
- 프로젝트 `isaac_sim/keyboard_drive.py`, `drive_controls.py`, `teleop_bridge.py`: 키보드 조작, 절대각 대응, 속도 단계, 제한·재활성화.
- [LeRobot 0.6.1 SOLeader 구현](https://github.com/huggingface/lerobot/blob/v0.6.1/src/lerobot/teleoperators/so_leader/so_leader.py): 연결·보정·위치 읽기 API.
- [NVIDIA Articulation Controller](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/robot_simulation/articulation_controller.html): 관절 위치·속도·힘 제어와 rad 단위.

## 제작 시 실제 확인

- 실제 리더 USB를 열지 않고 sim 모드로 촬영했습니다.
- 팔 기본 자세 유지 표시, W 전진 명령, 이동키 해제 후 STOP, 1/2 속도 단계 변경, T 추적 시점을 확인했습니다.
- 초기 구현에서 Space와 기본 재생 단축키의 충돌을 확인했습니다. 이후 주행 앱 실행 중 toolbar::play의 Space 등록만 해제하고 종료 시 복원하도록 수정했습니다. 수정 후 실제 Space 입력에서 PAUSE 이벤트가 발생하지 않는 것을 확인했고 03-stop 원본·강조 이미지를 갱신했습니다.
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


## 2026-09-09 초기화·화면 배치 갱신

- 1·2편은 편집값을 유지하는 Stop 기반 초기화, 5편은 저장 기록을 보존하는 모형 초기화를 추가했습니다.
- 3·4·6편은 좌측 Perspective·우측 Front Camera와 색상 라인별 랜덤 큐브 리셋을 공통 사용합니다.
- 변경된 시작·조작·기록 화면을 실제 Isaac Sim 5.1 Docker에서 새로 캡처했습니다. 기본 도형·카메라 속성 메뉴 등 변경 없는 상세 화면은 기존 검증 캡처를 유지합니다.
- 원본 PNG는 수정하지 않고 SVG의 빨간 테두리와 별도 설명 영역으로 강조했습니다. 캡처에 마우스 커서는 포함되지 않으며 버튼·상태가 보이는지 확인했습니다.
- 새 캡처의 고유 폴더 이름은 제작 중 임시 실습 결과 예시이며, 학생은 자신의 실행 로그에 나온 경로를 사용합니다.

## 손가락 충돌 형상 개선 · 2026-09-09

- 단일 Convex Hull이 손가락 안쪽 공간을 메우는 형상을 확인해 고정·이동 손가락 두 곳에 Convex Decomposition을 적용했습니다.
- 가상 시험의 비교 조건·결과·한계는 [전체 검증 기록](../VALIDATION.md)에 남겼습니다. 재생성한 ZIP에 집기 안내와 `./lekiwi test-gripper` 명령을 포함합니다.
- 공식 근거: [Isaac Sim 5.1 · Convex Decomposition](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/physics/simulation_fundamentals.html#convex-decomposition).
