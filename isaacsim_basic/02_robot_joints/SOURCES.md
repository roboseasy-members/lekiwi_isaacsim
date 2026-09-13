# 2편 출처와 화면 기록

## 공식 문서

- [Isaac Sim 5.1 물리 기초](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/physics/simulation_fundamentals.html)
- [로봇 Python 시작 예제](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/introduction/quickstart_isaacsim_robot.html)
- [관절 제어 API](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/robot_simulation/articulation_controller.html)
- [카메라 센서](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/sensors/isaacsim_sensors_camera.html)

문서를 참고해 프로젝트 교육용 예제를 직접 작성했습니다. 런타임 버전은 Isaac Sim 5.1.0입니다.
1~5장 학생 파일은 로봇 자산 없이 Isaac Sim Python으로 실행합니다. 6장은 프로젝트의 기록 형식과 로봇 자산을 사용합니다.

## 화면

2026-09-10 코드 실습 개편: 전용 Lesson 탭을 사용하지 않는 실제 Isaac Sim 화면을 캡처합니다.
원본은 images/screenshots, 빨간 표시 좌표와 설명은 images/annotations.json,
원본을 포함한 표시본은 SVG·PNG입니다. 코드는 Markdown 코드 블록으로 제시합니다.
기존 비교 사진은 과거 검증 자료일 수 있으며 현재 실행 안내는 README에 명시된 화면을 따릅니다.

[교재로 돌아가기](README.md)

## 2026-09-13 · 직접 제작과 코드 연결 보강

`gui.md`에 생성 메뉴·객체 경로·입력값·코드 대응·USD 저장 순서를 추가했습니다.
기존 스크린샷은 실제 5.1 촬영본에서 필요한 메뉴·속성 화면을 재사용했습니다. 사진의 장면·수치가 이번 실습과 다르면 본문에서 구분합니다.
삭제된 전용 Lesson·Record 버튼을 현재의 기본 기능으로 안내하지 않습니다.
화면 제작의 공통 환경·물리·관절·카메라 안내는 아래 5.1 공식 문서와 교재 코드를 대조했습니다.

- [Stage·PhysicsScene·조명 준비](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/robot_setup_tutorials/tutorial_intro_environment_setup.html)
- [물리 속성·재질 연결·관절](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/physics/simulation_fundamentals.html)
- [GUI에서 관절과 Drive 만들기](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/robot_setup_tutorials/tutorial_gui_simple_robot.html)
- [GUI에서 Camera 만들기](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/robot_setup_tutorials/tutorial_gui_camera_sensors.html)

실제 확인 범위와 미확인 항목은 [전체 검증 기록](../VALIDATION.md)에 구분해 남깁니다.

### 새로 촬영한 화면

2026-09-13, 로컬 RTX 5060 Laptop GPU에서 NVIDIA 공식 Isaac Sim 5.1.0 컨테이너를 실행했습니다.
단원 학생 코드로 기준 장면을 준비하고 실제 메뉴·속성을 열어 촬영했습니다. 관절·Camera 생성 메뉴와 TransformOp 추가는 마우스 입력으로 확인했습니다.
전체 장면을 처음부터 끝까지 마우스로 제작한 리허설 결과는 아닙니다. 카메라 수치 설정은 USD API로 적용한 뒤 실제 Property와 행렬을 확인했습니다.
촬영 원본은 앱 창 영역만 캡처한 `images/screenshots/`의 PNG이며, 아래 SHA256도 원본 기준입니다.
본문의 같은 이름 PNG에는 이후 빨간 테두리와 설명을 추가했습니다. 화면·수치·버튼은 합성하지 않았습니다.

- `08-create-joint.png` · SHA256 `04c4177b1816444d7150aa1c06e529a3d173043a5576ae0042e803d4eba409ba`
- `09-add-drive.png` · SHA256 `fa734e6973e068ca75705a96cc4c1d6baae5b1cf40340a5a2718c5a9d5b84abb`


## 2026-09-13 · 본문을 마우스 실습 우선 순서로 통합

직접 제작 안내를 README 앞부분에 통합하고 API·Python 수정·실행 설명은 마지막 절로 옮겼습니다.
실습 중간의 저장 시점과 기준값 복원을 명시하고, 기록지도 같은 순서로 구성했습니다.
`gui.md`는 이전 링크를 위한 본문 안내로 유지합니다. 아래 사진 재사용은 새 촬영이나 전체 GUI 리허설을 뜻하지 않습니다.


## 2026-09-13 · 누락된 빨간 박스 보완

본문에서 클릭·입력·확인할 대상을 실제 화면과 대조해 빨간 테두리로 표시했습니다.
`images/annotations.json`에 좌표와 설명을 기록하고 기존 SVG 생성기로 원본 PNG를 그대로 포함했습니다.
본문용 PNG는 SVG를 렌더링한 표시본이며, `images/screenshots/`의 원본과 구분합니다.
아래 SHA256은 원본 기준입니다. 이 작업은 재촬영이 아니며 화면의 메뉴·숫자는 변경하지 않았습니다.

| 원본 캡처 | SHA256 |
|---|---|
| `images/screenshots/08-create-joint.png` | `04c4177b1816444d7150aa1c06e529a3d173043a5576ae0042e803d4eba409ba` |
| `images/screenshots/09-add-drive.png` | `fa734e6973e068ca75705a96cc4c1d6baae5b1cf40340a5a2718c5a9d5b84abb` |
