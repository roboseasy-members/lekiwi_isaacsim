# 2편 출처·검증

대상: 저장소의 Isaac Sim 5.1.0 Docker. 문서 확인일: 2026-09-07.

- [NVIDIA: Articulate a Basic Robot](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/robot_setup_tutorials/tutorial_gui_simple_robot.html): 링크·관절·Articulation 구성 개념.
- [NVIDIA: Articulation Controller](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/robot_simulation/articulation_controller.html): 제어 초기화, 위치·속도·힘 명령, Python rad / USD degree 구분.
- [NVIDIA: Tuning Joint Drive Gains](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/robot_setup_tutorials/joint_tuning.html): 목표 추종과 구동값 조정.
- 프로젝트의 `isaac_sim/arm_control.py`, `arm_smoke_test.py`, `teleop_bridge.py`: 팔 기본 자세와 제어 구현.

NVIDIA 튜토리얼을 복제하지 않고, 로컬 기본 도형으로 관절 모형을 새로 구성했습니다.
실제 로봇 번들 출처는 저장소 `isaac_sim/assets/lekiwi_soarm/SOURCE.md`를 참조합니다.

## 실제 확인

- 교육용 USD·배포 관련 검사 41개 통과, 자산 재생성 검사 1개 제외.
- Docker `./lekiwi test-basic`: 기존 5개 물리 장면과 joints 통과.
- 관절의 실제 도달각: +30° 목표 → 29.999°, -30° → -30.000°, 80° → 60.000°.
- 한 관절 모형의 고정 받침 위치 유지 검사 통과.
- 낮은 Stiffness/Damping 비교는 관찰 과제입니다. 특정 정착 시간·흔들림 크기를 보장하는 자동 검사에는 포함하지 않았습니다.

- 실제 GUI에서 Ctrl+클릭으로 Target Position=30°를 입력하고 Play/Pause 결과를 확인했습니다.
- 실제 화면 5장의 객체 구조·앵커·제한·목표·구동값을 확인했습니다.

스크린샷 원본은 `images/screenshots/`, 강조 좌표는 `images/annotations.json`에 보관합니다.
원본을 포함한 SVG에 빨간 테두리와 아래 설명을 추가하고, 읽기·노션용 PNG를 렌더링합니다.
실제 하드웨어 보정·동작 검증은 이 편의 검사에 포함하지 않습니다.


## 2026-09-09 초기화·화면 배치 갱신

- 1·2편은 편집값을 유지하는 Stop 기반 초기화, 5편은 저장 기록을 보존하는 모형 초기화를 추가했습니다.
- 3·4·6편은 좌측 Perspective·우측 Front Camera와 색상 라인별 랜덤 큐브 리셋을 공통 사용합니다.
- 변경된 시작·조작·기록 화면을 실제 Isaac Sim 5.1 Docker에서 새로 캡처했습니다. 기본 도형·카메라 속성 메뉴 등 변경 없는 상세 화면은 기존 검증 캡처를 유지합니다.
- 원본 PNG는 수정하지 않고 SVG의 빨간 테두리와 별도 설명 영역으로 강조했습니다. 캡처에 마우스 커서는 포함되지 않으며 버튼·상태가 보이는지 확인했습니다.
- 새 캡처의 고유 폴더 이름은 제작 중 임시 실습 결과 예시이며, 학생은 자신의 실행 로그에 나온 경로를 사용합니다.
