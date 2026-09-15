# 1편 출처와 화면 기록

## 공식 문서

- [Isaac Sim 5.1 물리 기초](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/physics/simulation_fundamentals.html)
- [로봇 Python 시작 예제](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/introduction/quickstart_isaacsim_robot.html)
- [관절 제어 API](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/robot_simulation/articulation_controller.html)
- [카메라 센서](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/sensors/isaacsim_sensors_camera.html)
- [Physics Scene 생성 직후의 Earth Gravity 기본 표시](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/robot_setup_tutorials/tutorial_intro_environment_setup.html#creating-the-physics-scene)
- [Gravity Magnitude의 기본값과 단위](https://docs.omniverse.nvidia.com/kit/docs/omni_physics/107.3/dev_guide/schemas/usdphysics.html): 기본값은 장면 길이 단위에 맞춘 지구 중력을 사용합니다.

문서를 참고해 프로젝트 교육용 예제를 직접 작성했습니다. 런타임 버전은 Isaac Sim 5.1.0입니다.
1~5장 학생 파일은 로봇 자산 없이 Isaac Sim Python으로 실행합니다. 6장은 프로젝트의 기록 형식과 로봇 자산을 사용합니다.

### Earth Gravity 입력 안내 확인

2026-09-15 학생 리허설에서 `Earth Gravity` 표시를 Ctrl+클릭해도 입력되지 않는 상황이 보고되었습니다.
로컬 `lekiwi-sim:0.1.0` 이미지의 `omni.kit.property.physx-107.3.26+107.3.3.cp311.u353` 구현을 읽어 확인했습니다.
`database.py`는 `physics:gravityMagnitude`의 기본값을 `Earth Gravity`로 표시하고,
`widgets.py`는 기본값 표시와 속성 우클릭 메뉴의 `Set Minimum`을 구성합니다. 이 속성의 최솟값은 `0`입니다.
기본값의 의미·교재 사진이 숫자 입력 후 화면이라는 점·숫자로 전환하는 메뉴를 본문에 설명했습니다.
확장 코드는 수정하거나 교재로 복사하지 않았습니다. 이후 아래 2026-09-15 상세 촬영에서 로컬 장비의 해당 메뉴와 숫자 입력을 확인했습니다. 학생 장비에서의 입력 성공과는 구분합니다.

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

- `18-disable-gravity.png` · SHA256 `c1ae74baed83a76cf63cfe2434dc91edbbc4ae8106adb6079e38daa5701ab7a8`
- `19-create-physics.png` · SHA256 `c2488dee24c91aeac758f3466744f32320e42fc1868ca26e98e11fad21cfd027`
- `20-add-mass.png` · SHA256 `879f295bbe994a99b8bbe46c41028bfcf945f68054da186510d5fbc25b4f3f6c`

- `21-empty-editor.png` · 새 `00_empty_stage.py`를 직접 실행해 빈 Stage와 Create 메뉴의 반응을 확인한 화면입니다. SHA256 `c80384a40879198bc97f89726afdbeb242d32afea6ca11ba9267580865f26d04`


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
| `images/screenshots/18-disable-gravity.png` | `c1ae74baed83a76cf63cfe2434dc91edbbc4ae8106adb6079e38daa5701ab7a8` |
| `images/screenshots/19-create-physics.png` | `c2488dee24c91aeac758f3466744f32320e42fc1868ca26e98e11fad21cfd027` |
| `images/screenshots/20-add-mass.png` | `879f295bbe994a99b8bbe46c41028bfcf945f68054da186510d5fbc25b4f3f6c` |
| `images/screenshots/21-empty-editor.png` | `c80384a40879198bc97f89726afdbeb242d32afea6ca11ba9267580865f26d04` |

## 2026-09-14 · 0장에서 1장으로 넘어가는 실행 안내 보완

수강생 리허설에서 브라우저 편집기 터미널(`/workspace/isaacsim_basic`)에 `./lekiwi basic`을 입력해
`No such file or directory`가 발생했습니다. 본문 시작을 `lesson stop` → `STOPPED` 확인 →
`lesson run --file .../00_empty_stage.py` → `READY` 확인 → WebRTC 재접속 순서로 안내했습니다.
브라우저 터미널의 표시와 사용할 명령을 명시하고 데스크탑 직접 실행 명령은 끝의 참고로 옮겼습니다.
이번 보완은 실행 위치와 장 전환 안내 수정이며, 1장 전체 마우스 실습의 검증 완료를 뜻하지 않습니다.

## 2026-09-15 · 단계별 Stage 구조와 사진 범위 정리

2절의 World·Light·PhysicsScene·Ground와 3절에서 추가하는 PracticeCube를 Stage 구조로 명시했습니다.
기존 비교 예제의 객체 목록이 현재 제작 단계처럼 보이지 않도록 앞부분의 세 큐브 전체 화면을 빼고,
실제 빈 편집 화면(`21-empty-editor`)에 Viewport·Property·Play 위치 표시를 추가했습니다.
`04-gravity`, `10-file`, `19-create-physics`는 기존 실제 촬영본의 속성·메뉴 영역만 표시합니다.

표시 범위는 `images/annotations.json`의 `crop`에 원본 기준 좌표로 기록했습니다.
기존 SVG 생성기에 영역 표시 기능을 추가했으며, 원본 PNG 바이트는 SVG 안에 그대로 포함합니다.
화면의 객체·메뉴·숫자를 합성하거나 재촬영하지 않았습니다. 본문용 PNG와 Notion ZIP도 함께 갱신했습니다.
이 정리는 단계별 안내와 사진의 불일치를 줄이는 작업이며, 학생 장비에서 전체 마우스 실습을 마쳤다는 뜻은 아닙니다.


## 2026-09-15 · 입문자를 위한 단계별 실제 화면 68장 추가

1장 1~7절을 선택할 객체 → 메뉴 → 입력 칸 → 결과 확인 순서로 나누었습니다.
0장 보완, 기존 비교 사진, 마지막 8절의 학생 Python 예제는 유지합니다.
새 사진은 이 저장소의 로컬 노트북(RTX 5060 Laptop GPU), `lekiwi-sim:0.1.0`의 Isaac Sim 5.1.0에서 촬영했습니다.
학생이 실습 중인 다른 노트북에 접속하거나 그 장면을 바꾸지 않았습니다.

### 촬영과 가공 범위

- 창의 실제 화면을 PNG로 캡처했습니다. 메뉴·문구·숫자를 합성하지 않았습니다.
- 시점별 장면의 객체·수치 일부는 임시 촬영 스크립트와 USD API로 준비했습니다. 전체 장면을 처음부터 끝까지 마우스로 제작했다는 의미는 아닙니다.
- 메뉴 열기, Xform 생성·World 이름 입력, Dome Light와 Physics Scene 생성, PhysicsScene을 World 아래로 드래그, 중력·질량 입력, Collider·Rigid Body·Mass 추가, Duplicate, 물리 재질 선택 창과 재질 연결 목록, Save As·Open 창은 실제 GUI로 조작했습니다.
- 원본은 `images/screenshots/22-empty.png`~`87-orient-input.png`의 68장입니다. 중간 번호의 `43a`, `62a`를 포함합니다.
- `images/annotations.json`에 빨간 박스 좌표·설명·확대할 영역을 기록했습니다. SVG는 원본 PNG 바이트를 그대로 포함하고 지정 영역을 보여 줍니다. 본문용 PNG는 이 SVG의 렌더링 결과입니다.
- 좁은 캡처에서도 설명이 잘리지 않도록 SVG 생성기에 선택적 설명 줄바꿈을 추가했습니다. 원본 PNG는 보존합니다.
- 강사용 비공개 대본은 Git 제외 상태를 유지합니다. 강사의 시간 배분은 전체 사진 수와 별개입니다.

### 실제 확인한 조작과 결과

- World를 선택해도 Physics Scene이 루트 `/PhysicsScene`에 생성될 수 있었습니다. Stage 드래그 후 실제 경로 `/World/PhysicsScene`을 확인했습니다.
- Gravity Magnitude의 우클릭 `Set Minimum` 이후 `9.81` 입력과 USD 값 반영을 확인했습니다. Mass의 `0.1` 입력도 확인했습니다.
- Shape Cube의 회전 줄이 `Orient`로 표시될 때 Y에 `15`를 입력해 실제 Y축 15도 회전 행렬이 되는 것을 확인했습니다. 별도 Rotate 속성을 추가할 필요가 없습니다.
- 파일 이름만 `.usda`로 입력하고 형식이 `*.usd`인 경우 실제 파일은 `.usd`로 저장되었습니다. 형식을 `*.usda`로 선택한 후 `base_scene.usda` 생성과 내용을 확인했습니다.
- 실제 GUI의 Physics materials 목록에서 Low를 선택한 뒤 RampLow의 physics 재질 연결 대상이 `/World/Low`인지 확인했습니다.
- 충돌을 추가한 큐브가 바닥에 멈췄을 때 중심 Z는 약 0.05 m였습니다. 두 경사면 실험에서 낮은 마찰의 큐브만 경사면 아래로 이동했습니다.
- 반발 실험의 실제 실행 후 일시정지한 화면에서 BallLow 중심 Z는 약 0.1500 m, BallHigh는 약 0.6634 m였습니다. 이 값은 촬영 시점의 높이이며 최대 반동 높이나 보장값이 아닙니다.

학생 장비의 전체 마우스 리허설은 계속 진행해야 합니다. 이 변경은 학생 코드·설치기·도커 이미지 변경이 아닙니다.

### 새 원본 SHA256

| 캡처 | SHA256 |
|---|---|
| `22-empty.png` | `228f7c5400368b05dcc0e26fbfc1bc3c7fd923f8533a124702005e4b8c515e1e` |
| `23-create-world.png` | `34a76860eed04244f817cb784afc0adfcc153c388ad8bacc9370e0e6e3e7dfb4` |
| `24-rename-menu.png` | `52d265c41723afc63354ba6d99177a203898066f11346d13a5901d8e8d6d4ad5` |
| `25-world-name.png` | `c72a6c57e2ec79e8d10f7acd3f4a89611ff9fe7d0a689664030949b0a5ea1fee` |
| `26-world-ready.png` | `3da524b91f878e7a1aa8d26877ac579305f5e66e0100b6e73637777d5770f57b` |
| `27-create-light.png` | `56164cdbd1d890a0df58d978f0683a6ad8e03d8373116d738415aa8b58fa18f1` |
| `28-light-name.png` | `cab89a28ca2d51fd3610e23c43499fc01b2e612856aafda43317e1a8279d67ab` |
| `29-light-intensity.png` | `5f0991afde9af0f9587ea04444482ea9cdb7181ec0a0e1a1f25531b3d060b166` |
| `30-create-physics.png` | `8b206018aafc4d5134b0ade2253beda24fa61cd9301dbf2ee429431c2c363ad5` |
| `31-physics-before-parent.png` | `ba6b056a0c71fac49e189409e289b6f3238484f1904eeae2c611742fcbe30dca` |
| `32-physics-drag-world.png` | `7e0d1079b4a4190a12dac770df570a14e3c0220ca7b230318691ce62f1c60f5d` |
| `33-earth-gravity.png` | `3011db2da7835f185ccc89c81bed067e1778312620fbc5295f152628231893f4` |
| `34-gravity-menu.png` | `4e89c7f0b578a89def6fd7e10db9f487d9b5ece60a3a0eab5c27d554f4add9bc` |
| `35-gravity-value.png` | `f606f35bd070d89be66c72aa953f80894992b5126ac25db886c9e35c7a59a32b` |
| `36-create-cube.png` | `d6fe5ac98b54d576987f331f1f83d194f5b2bbed98e7b68c6e0a27e8ce8d995b` |
| `37-ground-transform.png` | `9483af07f319a045e7b748a910b20ece6692d24a16166efd398810be6f1b50bb` |
| `38-ground-size.png` | `958dd28a53c71cbb3c67104648da9333a06e72463b701d2fa16bef0e8e19ad01` |
| `39-add-collider.png` | `2b6790cafdeafe5830587894acfb3857eef5c3579ee9288db41281ba958d5555` |
| `40-ground-collision.png` | `755aa46da0c893d9fade5bc97bedfc4b0b4b2dc3297f43dc09842d416c4318e9` |
| `41-base-stage.png` | `fb58d1502100c418696e94cb88223d1bcf0e6862fe83e670be26568b47b3e0e4` |
| `42-file-save-menu.png` | `6e816f7d0ba36e96d4bc35ebe1a2b37ffaefa356f18b65d1b2cb0451a7928699` |
| `43a-save-extension.png` | `792723324cdb54e3e7dc4506adc07a66509af93eb6dd8a755e238e97fd8a4354` |
| `43-save-dialog.png` | `0edcb9d7917118261cc953f6a2d0f7dc20a9fe22c07497bf43f1715aa52100e8` |
| `44-cube-transform.png` | `362ed575eac2c0547b9efb0c679488fb85a2226c87af9ab6fe99e50c4d508cf9` |
| `45-cube-size.png` | `515d41773145a444f64fd96c0ed0896d0f8061ef48cb59452114c7ae65d7b4ee` |
| `46-add-rigid-body.png` | `a277dc0fb154605656face3e297f3fbeebb2fc4f812cffbbb2379e6c9daab009` |
| `47-add-mass.png` | `59891154e4767ba7eb41aa45cebd4b3deaa69150fa828b6b58f724a2c6294852` |
| `51-cube-add-collider.png` | `8025b512496495d348b0e6ffc597b9cf91b6300a8173c54e0d8c26e44f7fd79d` |
| `48-mass-value.png` | `583b6478fef136e6b91354c44a6291e0e84d275d88601ad738b8396378f15151` |
| `49-gravity-off.png` | `5650fdee1d972cc596dbad2dad04cc00f6814ab2f0c11c447c8ff77971c7c4c4` |
| `50-gravity-on.png` | `ee5329e4ec269ab8da05fc2e66ee8c54337f60bb57abf4644e0faf580ee9e115` |
| `52-cube-collision.png` | `cd6ad32c307e058f4273c92c65f987a91252fa482ac87974df4c522142584647` |
| `53-play-ready.png` | `151ff050cf960e46c704229623dadef1aef173e6289dbdbfe698f9767cd5126d` |
| `54-playing.png` | `46641f71664318818348b58981eaae81ef502bc45e5610f519132d04b2159048` |
| `55-duplicate-menu.png` | `62281dffc1d4627ad4f3b028a18a8f60a276f92f8ccb7f7337b97d4965a6ddcb` |
| `56-light-transform.png` | `b6135b7ac25c5a77d01ad7ca6ca11fe519df42afa970989af001358bff9aa330` |
| `58-heavy-transform.png` | `d069d4d274f1d446a7223b0dddd5f8fbe93343c574027448e8bb5c025dca0fdc` |
| `57-light-mass.png` | `c32c83dbfc63f3c740a8c196757490f50b6bf6ad31de1326d6c5f634f6d433c3` |
| `59-heavy-mass.png` | `2c16eba6245f5f62d7b7c948bc72c0750d9ac3f79d7faa642882739f6c00f807` |
| `60-moon-gravity.png` | `6516c18cff1de3af455d2eed4284280cc8b4808e717ec9bccb3fb4261288b9b6` |
| `61-open-menu.png` | `52027f9b1eac98c368810803cdee216d636db53cdc20f5067bc8cfac899fee84` |
| `62-open-dialog.png` | `3ef7d51b090c2ca81cac3633b1d5c496957a3115db902d18274e7c82badaf5e2` |
| `62a-unsaved-dialog.png` | `1f83a1af026a1f1af9f0cc7f5289bd986e9d04d109d45cc3f7b58367850fe0ef` |
| `63-ramp-low-transform.png` | `6c180cbf48d2f9e9471e8bda1e124b8b541318c04f251094f78f9f2f770ca8ba` |
| `64-ramp-high-transform.png` | `7eeaa59307cea777bd2197e6a3c622440e4b43a1d94c888105844d63f3d5e6e8` |
| `65-friction-cube-low.png` | `c154b9f026a8ab9af3451889f23590ee53ae64f284d890a9c272e86ed09f1035` |
| `66-friction-cube-high.png` | `85234a608d01d915bec36a8c5f2edddefa78b562d4570aff50282b3838d9acd1` |
| `67-create-material.png` | `ead5832132e499fb8e58404aa94f21adc34ff6c18e46b61920350392c751af8d` |
| `68-material-type.png` | `cc0b2b3b986366a75abbff7ca8759eccb2597ecd244779df701690d6d5d7372f` |
| `69-low-friction.png` | `93ceacb18b1915f69787f9645a9137174447cda853927f0a3ebb31005710a718` |
| `70-high-friction.png` | `bf3f5a9d2227a1688c4b82665b8316ce6a0fbb7696944c9a6a01ac4096c81f23` |
| `83-restitution-high.png` | `64836c2a4afb00dfc8b307691bff0f54157fcaa12097e031a8b6e3417f05b655` |
| `71-physics-binding-menu.png` | `af7a9e6b9b08cf558413a7ed75e6a022f556959113499b1f7bdb6f12bccebea4` |
| `72-ramp-low-bound.png` | `3c98acbeac54023d47ea7e5a9a425e2f6fe7a49795d3e2312003364cf4ce677a` |
| `73-cube-low-bound.png` | `837c3025722b9e511635860acb7ba3be2a351d4d69e68540b5433c59eda776a0` |
| `74-cube-high-bound.png` | `6e308680d209b89a2acbdc635a59b8c3904c1fffe69225f45fece32f30cdca60` |
| `84-ball-binding.png` | `4d091cdbe5029b99198bff5d0a0341108ad4ca1076217de6e0eb82d4d4414609` |
| `75-friction-ready.png` | `8abb9344e8cbb935bdd1ae9f2801de733c12473f49f6bc46e7b0e79459efd632` |
| `76-friction-result.png` | `0a2b3cf9cf7386ead8839f6d36f5b9ad5bbdcf26ecb09af1262f492b249ab8d0` |
| `77-pad-low.png` | `4e1e62968468e9b641b7e5c2dcdeaf64143940ae68219db2f86845b0c2e77a2c` |
| `78-pad-high.png` | `cedebbebcf8a0d325472bb2e0d94cab52d20ce5e5842e4bbf03b929ae25fe959` |
| `79-create-sphere.png` | `0454c0c81c206f1150c2a4e3cdc690aa916f7e3826954bbd21b35863a78ef4a4` |
| `80-ball-low-transform.png` | `81b884c5f2e21499eb3dc99e29d61449558d5326fde2aeb993e99bc93f0c612c` |
| `82-ball-high-transform.png` | `f46973a79e09924f7098d8be99122def1f5b0acde72abdd89e25b713830eb438` |
| `81-ball-radius.png` | `63cc1610579caef522178467038f2a51a8b43130d7f2a5c0322eb44f65a24a36` |
| `85-bounce-ready.png` | `edb1b8c0faa64d5e68c01741738b85e303c4d7b1a1c81dc61241a358bb4d4c1d` |
| `86-bounce-result.png` | `54562119a088184884438ae21ca988d5e956884763e09c3c972278120d6e5e77` |
| `87-orient-input.png` | `5388c98f8bb710d7db6daee199c8a6612026c85a052f39674f2a95244568dcc6` |


### 변경 후 검사

68개 새 표시본의 빨간 박스 밖 픽셀을 원본의 해당 영역과 대조해 일치함을 확인했습니다.
89개 SVG의 내장 원본 바이트·SHA256, 확대 영역·박스 좌표 범위, 설명 글자의 가로·세로 범위 검사를 통과했습니다.
교재 26개 문서의 로컬 링크·이미지 227개, 셸 코드 블록 75개, Notion ZIP 7개의 무결성·본문·이미지 일치 검사를 통과했습니다.
8절 코드 설명과 학생 Python 파일은 변경하지 않았습니다. 촬영용 Isaac Sim은 종료했습니다.
