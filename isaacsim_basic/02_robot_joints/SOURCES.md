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
실습 중간의 저장 시점과 기준값 복원을 명시하고, 본문에서 마우스 실습과 코드 실행 결과를 비교하도록 구성했습니다.
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

## 2026-09-16 · 입문자용 클릭·입력 화면 보강

마우스로 제작 → 값 변경과 관찰 → 저장 → 마지막 코드 실습 순서로 본문을 세분화했습니다.
선택할 객체의 경로, 클릭할 메뉴, 입력할 숫자를 분리하고 실제 화면에 빨간 박스를 추가했습니다.

이번 장 표시본은 새 촬영 기반 18개, 기존 실제 화면 재사용 16개입니다. 여러 장에서 공유하는 촬영은 중복 집계됩니다.
원본 PNG는 `images/screenshots/`, 빨간 박스와 설명은 SVG 및 `annotations.json`, 본문 표시본은 PNG입니다.
화면 내용을 합성하거나 숫자를 이미지 편집으로 바꾸지 않았습니다. SVG는 원본 PNG 바이트를 그대로 포함하며 화면 밖에 설명을 붙입니다.

### 촬영·확인 범위

재부팅 후 RTX 5060 Laptop GPU와 NVIDIA 드라이버 580.178.04가 정상 인식되는 환경에서 Isaac Sim 5.1 실제 GUI를 촬영했습니다.
촬영용 부품·속성 배치 일부는 별도 임시 USD/API로 준비했습니다. 따라서 이 자료는 모든 객체를 처음부터 마우스로 제작한 전체 학생 리허설의 기록은 아닙니다.

FixedBase의 Body 선택 창에서 Base 선택·확정, Property의 목표 각도 입력, Play/Stop을 확인했습니다. 실제 각도는 목표 +30°에 +29.9999°, -30°에 -29.9999°, 목표 80°에 상한 약 60.0002°였습니다.

기존 학생 Python 코드는 수정하지 않았습니다. 코드 검증은 촬영 앱을 재사용한 범위이며, 일반 실행 명령 전체·새 PC 설치·실물 USB 리더·데이터 업로드·학습을 이번에 다시 시험한 것은 아닙니다. 자세한 결과는 [검증 기록](../VALIDATION.md)에 있습니다.

### 원본 출처

| 표시본 | 원본 출처 | 원본 SHA256 |
|---|---|---|
| `step-base-transform` | 2026-09-16 실제 촬영, `images/screenshots/step-base-transform.png` | `9fff39e1bfcecb93dd97a73b2f0c7e39a4ed4fcb7e85b22c2b85c32cff7261f6` |
| `step-base-mass` | 2026-09-16 실제 촬영, `images/screenshots/step-base-mass.png` | `98dd617e265e672bfdc790d6e7910514cfecb00c51ab263800963c7e3f685a54` |
| `step-arm-mass` | 2026-09-16 실제 촬영, `images/screenshots/step-arm-mass.png` | `969644070dfd8b56c3058f5623f3ab55dd6b6fc745511f50f7d9793a24be2460` |
| `step-fixed-target-dialog` | 2026-09-16 실제 촬영, `images/screenshots/step-fixed-target-dialog.png` | `fcc61949b1001a6c527aafe5cfed2854043793fd3063a76a1d7ad82d5f0fd8b0` |
| `step-target-input` | 2026-09-16 실제 촬영, `images/screenshots/step-target-input.png` | `1a7a7ebd49e052b41c63fcaea96c595cf9129b982991878417afc6297e95825e` |
| `step-base-shape` | 2026-09-16 실제 촬영, `images/screenshots/step-base-shape.png` | `9b61c08b3f8c44e6b72543bc3f233f6819c27b2a319201d7c21bf25a84fa0195` |
| `step-arm-transform` | 2026-09-16 실제 촬영, `images/screenshots/step-arm-transform.png` | `ffd5e391b37bf2be32324d4672e54af83655a1b47cd58e765380f90040369162` |
| `step-arm-shape` | 2026-09-16 실제 촬영, `images/screenshots/step-arm-shape.png` | `7cb60f5a3550a02fc2446bfb4e8ec81bcbfba209f38747ab90100573878f2d47` |
| `step-shape-size` | 2026-09-16 실제 촬영, `images/screenshots/step-shape-size.png` | `6c73b7dc74ddb9f0216054f2a48aab883145f32ef6f489cc785f7f17e952dd75` |
| `guide-body-target` | 2026-09-16 실제 촬영, `images/screenshots/guide-body-target.png` | `a3de9a81d5b93f5a981ed6a1055d96b5169cb46bd513a0387ef597640201a164` |
| `step-fixed-local` | 2026-09-16 실제 촬영, `images/screenshots/step-fixed-local.png` | `3cec10e2cc43b4ab755c64934f5c169ce0c4b5dcf80cc26d1604e0ce878c0bc8` |
| `step-fixed-root` | 2026-09-16 실제 촬영, `images/screenshots/step-fixed-root.png` | `2caaf0c5844727c8ac608bcbb87c00bb66394cd33f15efcc52c3bb863ec8b04a` |
| `step-shoulder-body` | 2026-09-16 실제 촬영, `images/screenshots/step-shoulder-body.png` | `20a399564eb25012edd0a1eaa586f1e33258b0038dea618c54f8307a29854bf6` |
| `guide-joint-anchors` | 2026-09-16 실제 촬영, `images/screenshots/guide-joint-anchors.png` | `bb554da3639de6d31deea230f152492c3fd7d1b1688c7023f8376ffbec9311d7` |
| `guide-target-input` | 2026-09-16 실제 촬영, `images/screenshots/guide-target-input.png` | `6e45b1547441d0db54ab0ecaa31f73bfa7c558cc3516b0ffefca16279674ad02` |
| `guide-angle-result` | 2026-09-16 실제 촬영, `images/screenshots/guide-angle-result.png` | `6e45b1547441d0db54ab0ecaa31f73bfa7c558cc3516b0ffefca16279674ad02` |
| `step-angle-limit` | 2026-09-16 실제 촬영, `images/screenshots/step-angle-limit.png` | `b92e5394074bd9f9c204ec6f50908291aff3b10b12ef9e4b1d20fa4b276875c8` |
| `guide-save-format` | 2026-09-16 실제 촬영, `images/screenshots/guide-save-format.png` | `af0e73527ff3c0c7d28c12b05a92dcd81f992c21d390ab8366a0aec2c0f1c79b` |
| `guide-open-menu` | 기존 촬영: `01_object_physics/images/screenshots/61-open-menu.png` | `52027f9b1eac98c368810803cdee216d636db53cdc20f5067bc8cfac899fee84` |
| `guide-open-dialog` | 기존 촬영: `01_object_physics/images/screenshots/62-open-dialog.png` | `3ef7d51b090c2ca81cac3633b1d5c496957a3115db902d18274e7c82badaf5e2` |
| `guide-save-menu` | 기존 촬영: `01_object_physics/images/screenshots/42-file-save-menu.png` | `6e816f7d0ba36e96d4bc35ebe1a2b37ffaefa356f18b65d1b2cb0451a7928699` |
| `guide-create-xform` | 기존 촬영: `01_object_physics/images/screenshots/23-create-world.png` | `34a76860eed04244f817cb784afc0adfcc153c388ad8bacc9370e0e6e3e7dfb4` |
| `guide-rename` | 기존 촬영: `01_object_physics/images/screenshots/24-rename-menu.png` | `52d265c41723afc63354ba6d99177a203898066f11346d13a5901d8e8d6d4ad5` |
| `guide-create-cube` | 기존 촬영: `01_object_physics/images/screenshots/36-create-cube.png` | `d6fe5ac98b54d576987f331f1f83d194f5b2bbed98e7b68c6e0a27e8ce8d995b` |
| `guide-add-rigid-body` | 기존 촬영: `01_object_physics/images/screenshots/46-add-rigid-body.png` | `a277dc0fb154605656face3e297f3fbeebb2fc4f812cffbbb2379e6c9daab009` |
| `guide-add-mass` | 기존 촬영: `01_object_physics/images/screenshots/47-add-mass.png` | `59891154e4767ba7eb41aa45cebd4b3deaa69150fa828b6b58f724a2c6294852` |
| `guide-add-collider` | 기존 촬영: `01_object_physics/images/screenshots/39-add-collider.png` | `2b6790cafdeafe5830587894acfb3857eef5c3579ee9288db41281ba958d5555` |
| `guide-joint-tree` | 기존 촬영: `02_robot_joints/images/screenshots/01-structure.png` | `921fa14cadd1004e1c3f0c20f7bafb9c39cfd0c0d737fddea9c5c6f95c125c49` |
| `guide-joint-limits` | 기존 촬영: `02_robot_joints/images/screenshots/05-gains.png` | `023b9b2966a3ac1e76fb09d42b817c554958b1207a4e427dd6ee2a1618f9cde1` |
| `guide-drive-values` | 기존 촬영: `02_robot_joints/images/screenshots/05-gains.png` | `023b9b2966a3ac1e76fb09d42b817c554958b1207a4e427dd6ee2a1618f9cde1` |
| `guide-fixed-menu` | 기존 촬영: `02_robot_joints/images/screenshots/08-create-joint.png` | `04c4177b1816444d7150aa1c06e529a3d173043a5576ae0042e803d4eba409ba` |
| `guide-revolute-menu` | 기존 촬영: `02_robot_joints/images/screenshots/08-create-joint.png` | `04c4177b1816444d7150aa1c06e529a3d173043a5576ae0042e803d4eba409ba` |
| `guide-articulation-menu` | 기존 촬영: `02_robot_joints/images/screenshots/09-add-drive.png` | `fa734e6973e068ca75705a96cc4c1d6baae5b1cf40340a5a2718c5a9d5b84abb` |
| `guide-drive-menu` | 기존 촬영: `02_robot_joints/images/screenshots/09-add-drive.png` | `fa734e6973e068ca75705a96cc4c1d6baae5b1cf40340a5a2718c5a9d5b84abb` |

### 표시본과 Notion 자료 재생성

```bash
python3 isaacsim_basic/01_object_physics/images/build_annotations.py isaacsim_basic/02_robot_joints/images
/usr/bin/python3 isaacsim_basic/export_lessons.py isaacsim_basic/02_robot_joints
```
