# 3편 출처·검증

대상: Isaac Sim 5.1.0 Docker. 문서 확인일: 2026-09-07.

- [NVIDIA: Camera Sensors](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/sensors/isaacsim_sensors_camera.html): Create Camera, Viewport 시점, render product 개념.
- [OpenUSD: UsdGeomCamera](https://openusd.org/release/api/class_usd_geom_camera.html): 카메라 축, Aperture/Focal Length 및 Clipping 단위.
- 프로젝트 `isaac_sim/robot_cameras.py`, `assets/cameras/mounts.json`, `keyboard_drive.py`: 장착값, C/T/P 기능, 저장 경로.

임시 장착 위치는 프로젝트 모델 형상 기준이며 NVIDIA 문서가 제공한 실측값이 아닙니다.
TF 식은 좌표 변환의 합성 관계이며, 실제 보정값은 교육생이 측정해야 합니다.

## 실제 화면 확인

- Docker GUI에서 OVERVIEW → FRONT → WRIST 전환과 상태 표시를 확인했습니다.
- 현재 기본 자세에서 front는 코스 전방을 표시하고 wrist는 팔 부품에 크게 가려집니다.
  손목 영상은 가림 진단 예시입니다. 보정 완료나 작업 가능 시야로 보고하지 않습니다.
- Camera와 부모 optical frame을 선택하여 Aperture·Clipping·Translate 속성 및 Create Camera 메뉴를 확인했습니다.
- Focal Length 2배 변경 시 같은 바구니가 크게 보이는 실제 영상을 확인했습니다.
- 원본은 `images/screenshots/`, 강조 사각형·설명은 `images/annotations.json`입니다.
  UI 픽셀을 재구성하지 않고 SVG 테두리와 아래 설명을 추가해 PNG로 렌더링했습니다.
- 두 카메라 동시 촬영·640×480 고정 렌더링·동기화·실측 TF·다양한 팔 자세의 영상 가림은 이 과정에서 검증하지 않았습니다.
