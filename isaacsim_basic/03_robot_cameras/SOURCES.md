# 3편 출처와 화면 기록

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

- `09-create-practice-camera.png` · SHA256 `cd8a924ea34f2ba6c329970a4b6c0e17afeb1c875a8fa91006b4d5f55f597d3c`
- `10-camera-transform.png` · SHA256 `36b6eb439492588e89fd153ab4b7baf0d2f9b352ab62b7d6e7136e9ae23f56ce`
- `11-add-rotation.png` · SHA256 `d6f39a81e5a17dfc81240603294409533c6789a290146d443c8a1d30dcce28a5`


## 2026-09-13 · 본문을 마우스 실습 우선 순서로 통합

직접 제작 안내를 README 앞부분에 통합하고 API·Python 수정·실행 설명은 마지막 절로 옮겼습니다.
실습 중간의 저장 시점과 기준값 복원을 명시하고, 본문에서 마우스 실습과 코드 실행 결과를 비교하도록 구성했습니다.
`gui.md`는 이전 링크를 위한 본문 안내로 유지합니다. 아래 사진 재사용은 새 촬영이나 전체 GUI 리허설을 뜻하지 않습니다.


## 2026-09-13 · 누락된 빨간 박스 보완

본문에서 클릭·입력·확인할 대상을 실제 화면과 대조해 빨간 테두리로 표시했습니다.
`images/annotations.json`에 좌표와 설명을 기록하고 기존 SVG 생성기로 원본 PNG를 그대로 포함했습니다.
본문용 PNG는 SVG를 렌더링한 표시본이며, `images/screenshots/`의 원본과 구분합니다.
아래 SHA256은 원본 기준입니다. 이 작업은 재촬영이 아니며 화면의 메뉴·숫자는 변경하지 않았습니다.

| 원본 캡처 | SHA256 |
|---|---|
| `images/screenshots/09-create-practice-camera.png` | `cd8a924ea34f2ba6c329970a4b6c0e17afeb1c875a8fa91006b4d5f55f597d3c` |
| `images/screenshots/10-camera-transform.png` | `36b6eb439492588e89fd153ab4b7baf0d2f9b352ab62b7d6e7136e9ae23f56ce` |
| `images/screenshots/11-add-rotation.png` | `d6f39a81e5a17dfc81240603294409533c6789a290146d443c8a1d30dcce28a5` |

## 2026-09-16 · 입문자용 클릭·입력 화면 보강

마우스로 제작 → 값 변경과 관찰 → 저장 → 마지막 코드 실습 순서로 본문을 세분화했습니다.
선택할 객체의 경로, 클릭할 메뉴, 입력할 숫자를 분리하고 실제 화면에 빨간 박스를 추가했습니다.

이번 장 표시본은 새 촬영 기반 14개, 기존 실제 화면 재사용 7개입니다. 여러 장에서 공유하는 촬영은 중복 집계됩니다.
원본 PNG는 `images/screenshots/`, 빨간 박스와 설명은 SVG 및 `annotations.json`, 본문 표시본은 PNG입니다.
화면 내용을 합성하거나 숫자를 이미지 편집으로 바꾸지 않았습니다. SVG는 원본 PNG 바이트를 그대로 포함하며 화면 밖에 설명을 붙입니다.

### 촬영·확인 범위

재부팅 후 RTX 5060 Laptop GPU와 NVIDIA 드라이버 580.178.04가 정상 인식되는 환경에서 Isaac Sim 5.1 실제 GUI를 촬영했습니다.
촬영용 부품·속성 배치 일부는 별도 임시 USD/API로 준비했습니다. 따라서 이 자료는 모든 객체를 처음부터 마우스로 제작한 전체 학생 리허설의 기록은 아닙니다.

뷰포트 Cameras → Camera 선택, Focal Length 24→48→24, Stage에서 Camera를 CameraMount 아래로 드래그, 부모 X=0.3 이동과 Z=15° 회전·복원을 확인했습니다.

기존 학생 Python 코드는 수정하지 않았습니다. 코드 검증은 촬영 앱을 재사용한 범위이며, 일반 실행 명령 전체·새 PC 설치·실물 USB 리더·데이터 업로드·학습을 이번에 다시 시험한 것은 아닙니다. 자세한 결과는 [검증 기록](../VALIDATION.md)에 있습니다.

### 원본 출처

| 표시본 | 원본 출처 | 원본 SHA256 |
|---|---|---|
| `step-cube-transform` | 2026-09-16 실제 촬영, `images/screenshots/step-cube-transform.png` | `06e9a7d746ef057590564fca6989e06f4875974f396f3c19120de582127c93ab` |
| `guide-camera-position` | 2026-09-16 실제 촬영, `images/screenshots/guide-camera-position.png` | `e10485a09c8c1a70b9762514d05d6ac818224a1c4272d28fce59bc7a60cb873d` |
| `guide-camera-rotation` | 2026-09-16 실제 촬영, `images/screenshots/guide-camera-rotation.png` | `e10485a09c8c1a70b9762514d05d6ac818224a1c4272d28fce59bc7a60cb873d` |
| `guide-camera-focal` | 2026-09-16 실제 촬영, `images/screenshots/guide-camera-focal.png` | `b07e4e993dfb1dc36bbc735f7840cd5fd86b27563a98615e4920a26ba9e5648c` |
| `guide-lens-fields` | 2026-09-16 실제 촬영, `images/screenshots/guide-lens-fields.png` | `2266542467537a1dbc96ae054d360de28de9c3f0642c94b42e21fa2e5f0a5053` |
| `step-clipping` | 2026-09-16 실제 촬영, `images/screenshots/step-clipping.png` | `e112b04fd25c2702ed7465dd6dc1e5f3be2f6c8c51160c4e637ea3f43614aac6` |
| `step-camera-picker` | 2026-09-16 실제 촬영, `images/screenshots/step-camera-picker.png` | `0a80409e77aabd8c09b9c08784c38d54036ea431006354121cdb75cb4449244e` |
| `guide-camera-view` | 2026-09-16 실제 촬영, `images/screenshots/guide-camera-view.png` | `a4ab2024ebf00470ad0a8612f2a38affd742113afba3b6a60d34cbc864044e8f` |
| `step-focal48` | 2026-09-16 실제 촬영, `images/screenshots/step-focal48.png` | `393941df6cb773a26ef9fec10e34be18a4d87e023db46d421f1533381d0fa2fd` |
| `step-camera-parent` | 2026-09-16 실제 촬영, `images/screenshots/step-camera-parent.png` | `f361ae0937fbded2b2089e059640eb38f2db16ed15f47b74db0159800cd22773` |
| `step-mount-move` | 2026-09-16 실제 촬영, `images/screenshots/step-mount-move.png` | `12fa789566a1a51284854e4dd373fd135a6ad05c33beddb5f35eb5cfa08bdb25` |
| `step-mount-rotate` | 2026-09-16 실제 촬영, `images/screenshots/step-mount-rotate.png` | `b8f0fe3719e91890b3ae3a49d2533bc39dea7288dea426cf275fd18c07c5cdc2` |
| `guide-save-format` | 2026-09-16 실제 촬영, `images/screenshots/guide-save-format.png` | `65595aad8c742ea2dd82f104cb47172eef77ec5b071fef6cb1eeeb848538eb06` |
| `step-cube-size` | 2026-09-16 실제 촬영, `images/screenshots/step-cube-size.png` | `78a6b815c90a7ffaf8dfe9a31447cd6b653b3d5dc1c797196a386deff0f5bc07` |
| `guide-open-menu` | 기존 촬영: `01_object_physics/images/screenshots/61-open-menu.png` | `52027f9b1eac98c368810803cdee216d636db53cdc20f5067bc8cfac899fee84` |
| `guide-open-dialog` | 기존 촬영: `01_object_physics/images/screenshots/62-open-dialog.png` | `3ef7d51b090c2ca81cac3633b1d5c496957a3115db902d18274e7c82badaf5e2` |
| `guide-save-menu` | 기존 촬영: `01_object_physics/images/screenshots/42-file-save-menu.png` | `6e816f7d0ba36e96d4bc35ebe1a2b37ffaefa356f18b65d1b2cb0451a7928699` |
| `guide-create-cube` | 기존 촬영: `01_object_physics/images/screenshots/36-create-cube.png` | `d6fe5ac98b54d576987f331f1f83d194f5b2bbed98e7b68c6e0a27e8ce8d995b` |
| `guide-create-xform` | 기존 촬영: `01_object_physics/images/screenshots/23-create-world.png` | `34a76860eed04244f817cb784afc0adfcc153c388ad8bacc9370e0e6e3e7dfb4` |
| `guide-create-camera` | 기존 촬영: `03_robot_cameras/images/screenshots/09-create-practice-camera.png` | `cd8a924ea34f2ba6c329970a4b6c0e17afeb1c875a8fa91006b4d5f55f597d3c` |
| `guide-add-rotation` | 기존 촬영: `03_robot_cameras/images/screenshots/11-add-rotation.png` | `d6f39a81e5a17dfc81240603294409533c6789a290146d443c8a1d30dcce28a5` |

### 표시본과 Notion 자료 재생성

```bash
python3 isaacsim_basic/01_object_physics/images/build_annotations.py isaacsim_basic/03_robot_cameras/images
/usr/bin/python3 isaacsim_basic/export_lessons.py isaacsim_basic/03_robot_cameras
```
