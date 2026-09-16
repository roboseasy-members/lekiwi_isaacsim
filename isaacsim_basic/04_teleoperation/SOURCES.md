# 4장 · 빨주노초 맵 텔레옵 · 출처와 검증 범위

## 현재 수업 기준 · 2026-09-16 흐름 복원

기존 색상 코스를 실행하고 키보드 베이스와 USB SO101 리더암을 조작합니다.
현재 본문은 README이며, 아래 과거 관절 모형·코스 제작 안내 이력은 이번 장의 필수 진행 순서가 아닙니다.

- 실행 근거: [프로젝트 실행기](../../lekiwi), [코스와 조작](../../isaac_sim/keyboard_drive.py), [색상 맵](../../isaac_sim/color_course.py).
- 기록 근거: [공통 기록 코드](../06_lekiwi_dataset/experiments/01_lekiwi_recording.py).
- 변환·학습·추론: [학생 설정 파일](../06_lekiwi_dataset/experiments/), [ACT 실행기](../../tools/act/launch.py).
- `images/course-overview.png`: 4장의 실제 코스와 두 Viewport를 안내합니다. 기존 6장 키보드 기록 실행 원본을 재사용하며 새 실물 리더 검증 사진이 아닙니다.
- 원본: [기존 캡처](../06_lekiwi_dataset/images/screenshots/09-code-first.png). 이 장의 `images/screenshots/course-overview.png`에 바이트를 바꾸지 않고 복사했습니다.
- 원본 SHA256: `b2fcf4c3e373c7995ef4ddf5076625e8d125798973060bbb8b3a40b03551253a`.
- 표시본은 기존 SVG 주석 생성기로 빨간 박스·설명을 추가했습니다. 새 버튼·화면 내용을 합성하지 않습니다.

이번 변경은 문서·실행 선택·학생 설정과 관련 자동 검사를 대상으로 합니다.
실물 리더·GPU 학습·추론 화면을 이번 변경에서 새로 실행한 결과와 혼동하지 않습니다. 실제 추론은 최종 리허설에서 확인합니다.

## 공식 문서

- [Isaac Sim 5.1 물리 기초](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/physics/simulation_fundamentals.html)
- [로봇 Python 시작 예제](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/introduction/quickstart_isaacsim_robot.html)
- [관절 제어 API](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/robot_simulation/articulation_controller.html)
- [카메라 센서](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/sensors/isaacsim_sensors_camera.html)

문서를 참고해 프로젝트 교육용 예제를 직접 작성했습니다. 런타임 버전은 Isaac Sim 5.1.0입니다.
이하에는 이전 보충 예제와 화면의 이력이 포함돼 있습니다. 현재 수업의 1~3장은 기초 예제이며, 4~6장은 프로젝트 코스·리더·기록·학습 실행기를 사용합니다.

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


## 2026-09-13 · 본문을 마우스 실습 우선 순서로 통합

직접 제작 안내를 README 앞부분에 통합하고 API·Python 수정·실행 설명은 마지막 절로 옮겼습니다.
실습 중간의 저장 시점과 기준값 복원을 명시하고, 본문에서 마우스 실습과 코드 실행 결과를 비교하도록 구성했습니다.
`gui.md`는 이전 링크를 위한 본문 안내로 유지합니다. 아래 사진 재사용은 새 촬영이나 전체 GUI 리허설을 뜻하지 않습니다.

- `images/manual-joint-structure.png`: [02_robot_joints/images/01-structure.png](../02_robot_joints/images/01-structure.png)를 동일 바이트로 복사했습니다. 단일 장 노션 ZIP 안에서도 필요한 속성 화면을 볼 수 있도록 포함합니다.

- `images/manual-drive-target.png`: [02_robot_joints/images/03-drive.png](../02_robot_joints/images/03-drive.png)를 동일 바이트로 복사했습니다. 단일 장 노션 ZIP 안에서도 필요한 속성 화면을 볼 수 있도록 포함합니다.

## 2026-09-16 · 입문자용 클릭·입력 화면 보강

마우스로 제작 → 값 변경과 관찰 → 저장 → 마지막 코드 실습 순서로 본문을 세분화했습니다.
선택할 객체의 경로, 클릭할 메뉴, 입력할 숫자를 분리하고 실제 화면에 빨간 박스를 추가했습니다.

이번 장 표시본은 새 촬영 기반 4개, 기존 실제 화면 재사용 4개입니다. 여러 장에서 공유하는 촬영은 중복 집계됩니다.
원본 PNG는 `images/screenshots/`, 빨간 박스와 설명은 SVG 및 `annotations.json`, 본문 표시본은 PNG입니다.
화면 내용을 합성하거나 숫자를 이미지 편집으로 바꾸지 않았습니다. SVG는 원본 PNG 바이트를 그대로 포함하며 화면 밖에 설명을 붙입니다.

### 촬영·확인 범위

재부팅 후 RTX 5060 Laptop GPU와 NVIDIA 드라이버 580.178.04가 정상 인식되는 환경에서 Isaac Sim 5.1 실제 GUI를 촬영했습니다.
촬영용 부품·속성 배치 일부는 별도 임시 USD/API로 준비했습니다. 따라서 이 자료는 모든 객체를 처음부터 마우스로 제작한 전체 학생 리허설의 기록은 아닙니다.

my_joint 열기 창과 my_joint_control.usda 저장 창을 촬영했습니다. 현재 학생 코드의 키보드 콜백에 실제 J/L/K 키 입력을 전달해 +30°/-30°/0° 추종을 확인했습니다.

기존 학생 Python 코드는 수정하지 않았습니다. 코드 검증은 촬영 앱을 재사용한 범위이며, 일반 실행 명령 전체·새 PC 설치·실물 USB 리더·데이터 업로드·학습을 이번에 다시 시험한 것은 아닙니다. 자세한 결과는 [검증 기록](../VALIDATION.md)에 있습니다.

### 원본 출처

| 표시본 | 원본 출처 | 원본 SHA256 |
|---|---|---|
| `guide-target-input` | 2026-09-16 실제 촬영, `images/screenshots/guide-target-input.png` | `6e45b1547441d0db54ab0ecaa31f73bfa7c558cc3516b0ffefca16279674ad02` |
| `guide-angle-result` | 2026-09-16 실제 촬영, `images/screenshots/guide-angle-result.png` | `6e45b1547441d0db54ab0ecaa31f73bfa7c558cc3516b0ffefca16279674ad02` |
| `guide-save-format` | 2026-09-16 실제 촬영, `images/screenshots/guide-save-format.png` | `2eaa064dbcc6018d69136fe30a66ea438ae8cb76f3f62eb14d721cc176f5334a` |
| `guide-open-dialog` | 2026-09-16 실제 촬영, `images/screenshots/guide-open-dialog.png` | `56865a7a41676dc255951ffe98bf751918f903a7c26edb9c5c819617bbbb5cb5` |
| `guide-open-menu` | 기존 촬영: `01_object_physics/images/screenshots/61-open-menu.png` | `52027f9b1eac98c368810803cdee216d636db53cdc20f5067bc8cfac899fee84` |
| `guide-save-menu` | 기존 촬영: `01_object_physics/images/screenshots/42-file-save-menu.png` | `6e816f7d0ba36e96d4bc35ebe1a2b37ffaefa356f18b65d1b2cb0451a7928699` |
| `guide-joint-tree` | 기존 촬영: `02_robot_joints/images/screenshots/01-structure.png` | `921fa14cadd1004e1c3f0c20f7bafb9c39cfd0c0d737fddea9c5c6f95c125c49` |
| `guide-drive-values` | 기존 촬영: `02_robot_joints/images/screenshots/05-gains.png` | `023b9b2966a3ac1e76fb09d42b817c554958b1207a4e427dd6ee2a1618f9cde1` |

### 표시본과 Notion 자료 재생성

```bash
python3 isaacsim_basic/01_object_physics/images/build_annotations.py isaacsim_basic/04_teleoperation/images
/usr/bin/python3 isaacsim_basic/export_lessons.py isaacsim_basic/04_teleoperation
```
