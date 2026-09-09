# 3편 출처·검증

대상: Isaac Sim 5.1.0 Docker. 문서 확인일: 2026-09-07.

- [NVIDIA: Camera Sensors](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/sensors/isaacsim_sensors_camera.html): Create Camera, Viewport 시점, render product 개념.
- [OpenUSD: UsdGeomCamera](https://openusd.org/release/api/class_usd_geom_camera.html): 카메라 축, Aperture/Focal Length 및 Clipping 단위.
- 프로젝트 `isaac_sim/robot_cameras.py`, `assets/cameras/mounts.json`, `keyboard_drive.py`: 장착값, C/T/P 기능, 저장 경로.

현재 기본 장착 위치의 X·Z는 사용자가 제공한 SOARM base 기준 측면 도면에서 가져왔습니다. NVIDIA 문서가 제공한 실측값이 아닙니다. Y·방향·재현 자세의 가정은 설정 JSON과 교재에 기록했습니다.
TF 식은 좌표 변환의 합성 관계이며, 실제 보정값은 교육생이 측정해야 합니다.

## 실제 화면 재촬영 · 2026-09-08

- 도면 TF를 포함한 Docker 이미지에서 3편의 `LEKIWI_COURSE_LAYOUT=random ./lekiwi sim`을 실행했습니다.
- OVERVIEW → FRONT → WRIST 전환과 `command: STOP`을 확인했습니다.
  front는 전방 도로·바구니·큐브를, wrist는 집게 양쪽과 그 사이 바닥을 표시합니다.
- 시뮬레이션을 일시정지한 뒤 Camera와 부모 optical frame을 선택해 Aperture·Clipping·Translate 속성과 Create Camera 메뉴를 촬영했습니다.
- front의 Translate 표시가 새 JSON과 일치하는 것을 확인했습니다. Property 숫자는 일부 소수점을 반올림합니다.
- Focal Length를 14.96342 → 29.92684로 바꾸어 같은 위치의 바구니가 크게 보이는 것을 확인하고 14.96342로 복구했습니다.
  장면 편집은 저장하지 않고 종료했으며 다음 실행은 기본 JSON의 원래 광학 설정을 사용합니다.
- 실제 UI 화면 7장의 원본은 `images/screenshots/`, 강조 사각형·설명은 `images/annotations.json`입니다.
  커서는 설명 대상 밖으로 이동했습니다. 원본 픽셀을 바꾸지 않고 SVG 테두리와 아래 설명을 추가했습니다.
- 이번 재촬영은 기본 자세의 시점·속성 확인입니다. 다양한 팔 자세의 가림, 실물 장착 정밀도와 집기 품질은 별도 확인 대상입니다.

## 도면 TF 반영 후 확인

2026-09-08 기본 카메라 JSON에 SOARM base 기준 도면 치수를 반영하고 Docker 이미지를 다시 빌드했습니다.
실제 `record` GUI에서 두 RGB와 30프레임 저장을 확인했으며, 저장된 카메라 설정이 기본 JSON과 일치했습니다.
현재 3편 화면은 위 재촬영본으로 교체했습니다. 이번 검증은 최종 실물 보정이나 집기 품질 검증을 의미하지 않습니다.
자세한 범위는 [전체 검증 기록](../VALIDATION.md)을 참고하세요.


## 2026-09-09 초기화·화면 배치 갱신

- 1·2편은 편집값을 유지하는 Stop 기반 초기화, 5편은 저장 기록을 보존하는 모형 초기화를 추가했습니다.
- 3·4·6편은 좌측 Perspective·우측 Front Camera와 색상 라인별 랜덤 큐브 리셋을 공통 사용합니다.
- 변경된 시작·조작·기록 화면을 실제 Isaac Sim 5.1 Docker에서 새로 캡처했습니다. 기본 도형·카메라 속성 메뉴 등 변경 없는 상세 화면은 기존 검증 캡처를 유지합니다.
- 원본 PNG는 수정하지 않고 SVG의 빨간 테두리와 별도 설명 영역으로 강조했습니다. 캡처에 마우스 커서는 포함되지 않으며 버튼·상태가 보이는지 확인했습니다.
- 새 캡처의 고유 폴더 이름은 제작 중 임시 실습 결과 예시이며, 학생은 자신의 실행 로그에 나온 경로를 사용합니다.
