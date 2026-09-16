# 6장 · 변환·ACT 학습·추론 · 출처와 검증 범위

## 현재 수업 기준 · 2026-09-16 흐름 복원

5장 원본을 골라 변환·검사하고 ACT 학습과 저장 모델 추론을 진행합니다.
현재 본문은 README이며, 아래 과거 관절 모형·코스 제작 안내 이력은 이번 장의 필수 진행 순서가 아닙니다.

- 실행 근거: [프로젝트 실행기](../../lekiwi), [코스와 조작](../../isaac_sim/keyboard_drive.py), [색상 맵](../../isaac_sim/color_course.py).
- 기록 근거: [공통 기록 코드](../06_lekiwi_dataset/experiments/01_lekiwi_recording.py).
- 변환·학습·추론: [학생 설정 파일](../06_lekiwi_dataset/experiments/), [ACT 실행기](../../tools/act/launch.py).
- `images/convert-settings.png`: 기존 실제 편집 화면에서 현재도 같은 episode_ids·dataset_name·success_only 영역만 잘라 보여 줍니다. 과거 브라우저 실행 명령은 현재 절차로 안내하지 않습니다.
- 원본: [기존 캡처](../06_lekiwi_dataset/images/screenshots/11-browser-dataset.png). 이 장의 `images/screenshots/convert-settings.png`에 바이트를 바꾸지 않고 복사했습니다.
- 원본 SHA256: `0b592725873832dce63cb52ff55d371947d05f40df5605c833fa6a0e928620d3`.
- 표시본은 기존 SVG 주석 생성기로 빨간 박스·설명을 추가했습니다. 새 버튼·화면 내용을 합성하지 않습니다.

이번 변경은 문서·실행 선택·학생 설정과 관련 자동 검사를 대상으로 합니다.
실물 리더·GPU 학습·추론 화면을 이번 변경에서 새로 실행한 결과와 혼동하지 않습니다. 실제 추론은 최종 리허설에서 확인합니다.

## 공식 문서

- [Isaac Sim 5.1 물리 기초](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/physics/simulation_fundamentals.html)
- [로봇 Python 시작 예제](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/introduction/quickstart_isaacsim_robot.html)
- [관절 제어 API](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/robot_simulation/articulation_controller.html)
- [카메라 센서](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/sensors/isaacsim_sensors_camera.html)
- [Hugging Face Hub 폴더 업로드](https://huggingface.co/docs/huggingface_hub/main/en/guides/upload)
- [HfApi 토큰 직접 전달](https://huggingface.co/docs/huggingface_hub/main/en/package_reference/hf_api)
- [Hugging Face 사용자 토큰 보안](https://huggingface.co/docs/hub/security-tokens)
- [ViewportWindow의 UI 표시 영역 get_frame](https://docs.omniverse.nvidia.com/kit/docs/omni.kit.viewport.window/107.0.7/omni.kit.viewport.window/omni.kit.viewport.window.ViewportWindow.html)

문서를 참고해 프로젝트 교육용 예제를 직접 작성했습니다. 런타임 버전은 Isaac Sim 5.1.0입니다.
이하에는 이전 보충 예제와 화면의 이력이 포함돼 있습니다. 현재 수업의 1~3장은 기초 예제이며, 4~6장은 프로젝트 코스·리더·기록·학습 실행기를 사용합니다.

- [5.1 Replicator 비동기 렌더링과 프레임 누락](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/replicator_tutorials/troubleshooting.html#async-rendering-and-frame-skipping)

- [5.1 렌더 프레임 지연과 동기 설정](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/python_scripting/util_snippets.html#rendering-frame-delay)

## 화면

2026-09-10 코드 실습 개편: 전용 Lesson 탭을 사용하지 않는 실제 Isaac Sim 화면을 캡처합니다.
원본은 images/screenshots, 빨간 표시 좌표와 설명은 images/annotations.json,
원본을 포함한 표시본은 SVG·PNG입니다. 코드는 Markdown 코드 블록으로 제시합니다.
기존 비교 사진은 과거 검증 자료일 수 있으며 현재 실행 안내는 README에 명시된 화면을 따릅니다.

2026-09-11 `images/10-recording-status.png`: 서버에서 실행한 6장 실습의 WebRTC 화면에서 두 Viewport 영역을 직접 캡처했습니다.
실제 리더를 연결하지 않은 표시 검사이며, 빨간 수집 상태·에피소드 시간·프레임 수를 확인하는 예시입니다. 카메라 원본 영상에는 이 UI가 포함되지 않습니다.

[교재로 돌아가기](README.md)

2026-09-12 `images/11-browser-dataset.png`: 노트북 Chrome의 실제 브라우저 VS Code 화면을 캡처했습니다.
서버의 `03_convert_dataset.py`에서 에피소드·이름을 수정해 저장한 뒤 파일만 실행하고, `04_inspect_dataset.py`로 재검사한 결과입니다.
1개 에피소드·422프레임·30 FPS, LeRobot v3 변환과 재열기를 확인했습니다. 커서가 설정과 결과를 가리지 않는지 확인했습니다.


## ACT 학습·추론 구현 근거

- [LeRobot ACT 공식 안내](https://huggingface.co/docs/lerobot/act)
- [LeRobot 0.6.1 ACT 구현](https://github.com/huggingface/lerobot/blob/v0.6.1/src/lerobot/policies/act/modeling_act.py)

공식 학습기와 저장된 전·후처리기, ACT의 `select_action`·`reset`을 호출합니다.
학생 설정·작업 수명 관리·Isaac Sim 카메라와 제어 연결은 이 프로젝트에 맞춰 작성했습니다.
모델 계산 동안 물리 시간을 멈추어 수집과 동일한 시뮬레이션 30 FPS 행동 간격을 유지하는 구조입니다.
변환 데이터 900프레임을 사용한 ACT 학습 1회·모델 저장과 추론 시작·정지·재시작은
[2026-09-13 실제 실행 기록](../../docs/act-rehearsal-20260913.md)에서 확인했습니다.
현재 교재는 같은 변환·학습·추론 기반을 사용합니다. 수정한 로컬 교재의 전체 진행과 수업용 노트북 확인은 최종 리허설 범위입니다.

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

- `images/manual-create-cube.png`: [01_object_physics/images/11-create-cube.png](../01_object_physics/images/11-create-cube.png)를 동일 바이트로 복사했습니다. 단일 장 노션 ZIP 안에서도 필요한 속성 화면을 볼 수 있도록 포함합니다.

- `images/manual-basket-colliders.png`: [01_object_physics/images/08-basket-colliders.png](../01_object_physics/images/08-basket-colliders.png)를 동일 바이트로 복사했습니다. 단일 장 노션 ZIP 안에서도 필요한 속성 화면을 볼 수 있도록 포함합니다.

- `images/manual-camera-properties.png`: [03_robot_cameras/images/04-camera-properties.png](../03_robot_cameras/images/04-camera-properties.png)를 동일 바이트로 복사했습니다. 단일 장 노션 ZIP 안에서도 필요한 속성 화면을 볼 수 있도록 포함합니다.

- 고정 관찰 카메라의 `Camera > Create from View`는 [NVIDIA 5.1 카메라 안내](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/robot_setup_tutorials/tutorial_gui_camera_sensors.html)의 메뉴를 사용합니다. 이번 변경에서는 해당 메뉴를 새로 촬영하지 않았습니다.


## 2026-09-13 · 누락된 빨간 박스 보완

본문에서 클릭·입력·확인할 대상을 실제 화면과 대조해 빨간 테두리로 표시했습니다.
`images/annotations.json`에 좌표와 설명을 기록하고 기존 SVG 생성기로 원본 PNG를 그대로 포함했습니다.
본문용 PNG는 SVG를 렌더링한 표시본이며, `images/screenshots/`의 원본과 구분합니다.
아래 SHA256은 원본 기준입니다. 이 작업은 재촬영이 아니며 화면의 메뉴·숫자는 변경하지 않았습니다.

| 원본 캡처 | SHA256 |
|---|---|
| `images/screenshots/10-recording-status.png` | `b375207ac73a3e90e702e8aef531f4dee57d8abb404911d214299ef08190a318` |
| `images/screenshots/11-browser-dataset.png` | `0b592725873832dce63cb52ff55d371947d05f40df5605c833fa6a0e928620d3` |

## 2026-09-16 · 입문자용 클릭·입력 화면 보강

마우스로 제작 → 값 변경과 관찰 → 저장 → 마지막 코드 실습 순서로 본문을 세분화했습니다.
선택할 객체의 경로, 클릭할 메뉴, 입력할 숫자를 분리하고 실제 화면에 빨간 박스를 추가했습니다.

이번 장 표시본은 새 촬영 기반 22개, 기존 실제 화면 재사용 8개입니다. 여러 장에서 공유하는 촬영은 중복 집계됩니다.
원본 PNG는 `images/screenshots/`, 빨간 박스와 설명은 SVG 및 `annotations.json`, 본문 표시본은 PNG입니다.
화면 내용을 합성하거나 숫자를 이미지 편집으로 바꾸지 않았습니다. SVG는 원본 PNG 바이트를 그대로 포함하며 화면 밖에 설명을 붙입니다.

### 촬영·확인 범위

재부팅 후 RTX 5060 Laptop GPU와 NVIDIA 드라이버 580.178.04가 정상 인식되는 환경에서 Isaac Sim 5.1 실제 GUI를 촬영했습니다.
촬영용 부품·속성 배치 일부는 별도 임시 USD/API로 준비했습니다. 따라서 이 자료는 모든 객체를 처음부터 마우스로 제작한 전체 학생 리허설의 기록은 아닙니다.

GUI에서 /LeKiwi에 제공 USD를 Reference로 연결하고 Colliders → Selected 표시, Play/Stop 낙하, Create from View를 확인했습니다. DropCube는 시작 Z=0.4 m에서 바구니 안 Z≈0.014 m에 안착했고 Stop으로 복원됐습니다. OverviewCamera의 초점거리 두 배 변경과 복원도 확인했습니다.

기존 학생 Python 코드는 수정하지 않았습니다. 코드 검증은 촬영 앱을 재사용한 범위이며, 일반 실행 명령 전체·새 PC 설치·실물 USB 리더·데이터 업로드·학습을 이번에 다시 시험한 것은 아닙니다. 자세한 결과는 [검증 기록](../VALIDATION.md)에 있습니다.

### 원본 출처

| 표시본 | 원본 출처 | 원본 SHA256 |
|---|---|---|
| `step-robot-transform` | 2026-09-16 실제 촬영, `images/screenshots/step-robot-transform.png` | `41cf29efdafce373490c7887439b7549219988c6c28f8c206cf5bc6c220053d3` |
| `step-ground-transform` | 2026-09-16 실제 촬영, `images/screenshots/step-ground-transform.png` | `cd3cccd1fcd391022ee3361940f326286d426ffe0f250695f20f5e21a45a06d6` |
| `step-cube-transform` | 2026-09-16 실제 촬영, `images/screenshots/step-cube-transform.png` | `8ae590d1e7b66a37792dca40338c7c72f96ada032e74cfa17b9c56d77864080b` |
| `step-basket-transform` | 2026-09-16 실제 촬영, `images/screenshots/step-basket-transform.png` | `588233ba03aa240071dafd99d96fe058e189f92347fddb8b64f24e903a854568` |
| `step-bottom-transform` | 2026-09-16 실제 촬영, `images/screenshots/step-bottom-transform.png` | `8b9cd492f8b5bdd8a82eb6a815ee96a115fea512c5a8097921e3a3059c915942` |
| `step-left-transform` | 2026-09-16 실제 촬영, `images/screenshots/step-left-transform.png` | `3c6514f2a0752098a150e2298c746ab6c0ce3186f121011bd54c2b2b23e40ff3` |
| `step-right-transform` | 2026-09-16 실제 촬영, `images/screenshots/step-right-transform.png` | `b4f053ef3f3c7e8eae639adbd9d2ff46761ac94d9d22bcdf0a30f1345b8703ca` |
| `step-front-transform` | 2026-09-16 실제 촬영, `images/screenshots/step-front-transform.png` | `8826713e9fce0f2c1370f162bf7c97ddc6586bfaca5ea15f650264e89e59cc7e` |
| `step-back-transform` | 2026-09-16 실제 촬영, `images/screenshots/step-back-transform.png` | `026254f29d7d5db3dc8098f263085c6aaf68f9427850388ce03b75097f4402e0` |
| `step-drop-transform` | 2026-09-16 실제 촬영, `images/screenshots/step-drop-transform.png` | `d24f1450a5896c28505f16c192dac47519a1f80748acc5ec78268c444dc82115` |
| `guide-add-reference` | 2026-09-16 실제 촬영, `images/screenshots/guide-add-reference.png` | `60ae7978a0fe47757260f40c5f84973a14c8a722c15635106e07361db3fab56e` |
| `step-reference-file` | 2026-09-16 실제 촬영, `images/screenshots/step-reference-file.png` | `410d71b6440c2a2da895e2d1c9c5c6815393f9e996341db04ec74f39992c99e9` |
| `step-cube-size` | 2026-09-16 실제 촬영, `images/screenshots/step-cube-size.png` | `ef375fb3204f8cd8b478a9f4b269f277ac99aca2b93cda9af33fb5c281b7075d` |
| `step-cube-mass` | 2026-09-16 실제 촬영, `images/screenshots/step-cube-mass.png` | `30bba87893e7e1272f673b94fa09d71f93a3a83d372d12dd703a1643040bce21` |
| `step-collider-menu` | 2026-09-16 실제 촬영, `images/screenshots/step-collider-menu.png` | `37584e613d0907d084e65ab0f2818888a3719ae1cf5dfd2bc289cf124de743cc` |
| `step-basket-colliders` | 2026-09-16 실제 촬영, `images/screenshots/step-basket-colliders.png` | `b35f30aad03d7e0eec91362f16a205284d9131573d0d5bf0876348f468bcad2b` |
| `step-drop-result` | 2026-09-16 실제 촬영, `images/screenshots/step-drop-result.png` | `23528d151adf4dc0c91873db1d34166bd3491b5be29aea32556638875186a042` |
| `step-create-from-view` | 2026-09-16 실제 촬영, `images/screenshots/step-create-from-view.png` | `e9dcfb947cc4ca16f37fe8d99eddfeea77fbb8a0419d39d36271a3ea716de9b8` |
| `guide-view-menu` | 2026-09-16 실제 촬영, `images/screenshots/guide-view-menu.png` | `e6afe7707fa989b01015266a5bf5c9b3caba561cda0842c75f456637ca2c6167` |
| `guide-camera-focal` | 2026-09-16 실제 촬영, `images/screenshots/guide-camera-focal.png` | `f68e009ecff8558bbebcc81c387219394e2542ef79e3f52b78a0176bc215300c` |
| `step-save-scene` | 2026-09-16 실제 촬영, `images/screenshots/step-save-scene.png` | `7caaa99a1eb15480be712689d36e312c0b35b3104bb3a0c254545774dfd68a71` |
| `guide-save-format` | 2026-09-16 실제 촬영, `images/screenshots/guide-save-format.png` | `7caaa99a1eb15480be712689d36e312c0b35b3104bb3a0c254545774dfd68a71` |
| `guide-open-menu` | 기존 촬영: `01_object_physics/images/screenshots/61-open-menu.png` | `52027f9b1eac98c368810803cdee216d636db53cdc20f5067bc8cfac899fee84` |
| `guide-open-dialog` | 기존 촬영: `01_object_physics/images/screenshots/62-open-dialog.png` | `3ef7d51b090c2ca81cac3633b1d5c496957a3115db902d18274e7c82badaf5e2` |
| `guide-save-menu` | 기존 촬영: `01_object_physics/images/screenshots/42-file-save-menu.png` | `6e816f7d0ba36e96d4bc35ebe1a2b37ffaefa356f18b65d1b2cb0451a7928699` |
| `guide-create-xform` | 기존 촬영: `01_object_physics/images/screenshots/23-create-world.png` | `34a76860eed04244f817cb784afc0adfcc153c388ad8bacc9370e0e6e3e7dfb4` |
| `guide-create-cube` | 기존 촬영: `01_object_physics/images/screenshots/36-create-cube.png` | `d6fe5ac98b54d576987f331f1f83d194f5b2bbed98e7b68c6e0a27e8ce8d995b` |
| `guide-add-rigid-body` | 기존 촬영: `01_object_physics/images/screenshots/46-add-rigid-body.png` | `a277dc0fb154605656face3e297f3fbeebb2fc4f812cffbbb2379e6c9daab009` |
| `guide-add-mass` | 기존 촬영: `01_object_physics/images/screenshots/47-add-mass.png` | `59891154e4767ba7eb41aa45cebd4b3deaa69150fa828b6b58f724a2c6294852` |
| `guide-add-collider` | 기존 촬영: `01_object_physics/images/screenshots/39-add-collider.png` | `2b6790cafdeafe5830587894acfb3857eef5c3579ee9288db41281ba958d5555` |

### 표시본과 Notion 자료 재생성

```bash
python3 isaacsim_basic/01_object_physics/images/build_annotations.py isaacsim_basic/06_lekiwi_dataset/images
/usr/bin/python3 isaacsim_basic/export_lessons.py isaacsim_basic/06_lekiwi_dataset
```
