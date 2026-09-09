# 출처와 검증 범위

## 문서 기준

- 대상 실행 환경: 이 저장소의 `nvcr.io/nvidia/isaac-sim:5.1.0` Docker 이미지.
- 공식 문서 확인일: 2026-09-07.
- [Adding Props](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/core_api_tutorials/tutorial_core_adding_props.html):
  물리 속성을 단계적으로 추가하는 학습 순서, 질량, 충돌 표시, 물리 재질.
- [Physics Simulation Fundamentals](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/physics/simulation_fundamentals.html):
  부모·자식 강체 구조, 정적 충돌, 충돌 근사, CCD, 접촉 여유 거리와 계산 간격.

설명은 이 프로젝트의 실습에 맞춰 새로 작성했습니다. NVIDIA 예제 자산을 복사하지 않았습니다.
`../scenes.py`는 기본 Cube/Sphere/Xform으로 독립 장면을 생성합니다.
교재의 수치와 비교 장면은 본 교육용 예시이며 실제 로봇의 측정값이 아닙니다.

## 검증 방법

- `../test_scenes.py`: USD 단위, 외부 의존성 없음, 물리 속성 차이, 재질 연결,
  바구니 개구부와 이전 작업 보존을 확인합니다. PhysX 동작 검증과 구분합니다.
- `./lekiwi test-basic`: Docker에서 실제 PhysX를 실행하여 다섯 비교 장면을 검증합니다.
- GUI 클릭 위치와 캡처는 실제 화면 확인 여부를 별도로 기록합니다.
  공식 문서에서 확인한 메뉴 경로를 실제 캡처라고 표현하지 않습니다.

## 2026-09-07 작성 시 확인

- 교육용 USD 검사와 관련 배포 검사: 39개 통과. 별도 로봇 자산 재빌드·외부 셰이더 검사 2개 제외.
- 기존 `tests/` 회귀 검사: 176개 통과, 환경 의존 검사 6개 건너뜀.
- Bash/Python 구문, Markdown 내부 파일 링크, SVG 구문, `git diff --check` 통과.
- Docker 이미지 빌드 성공. `./lekiwi test-basic`에서 drop / mass / friction / bounce / basket
  모두 PASS 및 최종 `ISAACSIM_BASIC_TEST result=PASS`를 확인했습니다.
- 실제 GUI에서 물리 편집 확장 `omni.physx.bundle` 활성화 후 Add → Physics,
  질량·중력·마찰·반발력 속성, 충돌 표시, Create → Shape → Cube, File 메뉴를 확인했습니다.
  기본 Python 실행 환경에 편집 메뉴가 없는 문제를 발견해 `run.py`에 확장 자동 활성화를 추가했습니다.
- 실제 GUI에서 바구니의 충돌 윤곽과 Play 후 큐브 안착을 확인했습니다.
- 새 Docker 이미지로 재실행할 때 편집 확장 활성화 직후 첫 장면을 여는 구간에서
  Sdf 콜백 충돌이 발생했습니다. 장면을 먼저 열고 초기 업데이트를 마친 뒤 확장을 켜도록
  순서를 변경했으며, 재빌드 후 `ISAACSIM_BASIC ready lesson=basket`와 실제 GUI 표시를 확인했습니다.
- `images/physics-components.svg`는 직접 작성한 개념도이며 Isaac Sim 화면 캡처가 아닙니다.

## 스크린샷과 표시 방식

- `images/screenshots/*.png`: 이 프로젝트의 Docker Isaac Sim 5.1.0 창을 직접 촬영한 원본 11장.
  바탕화면의 다른 앱과 사용자 작업 내용은 포함하지 않았습니다.
- 촬영일: 2026-09-07. Property와 메뉴는 실제 UI이며 생성형 이미지로 재구성하지 않았습니다.
- 입력값·버튼 이름·관찰 대상을 가리지 않도록 마우스 위치를 확인했습니다.
- `images/annotations.json`: 각 화면에서 강조할 사각형과 설명.
- `images/build_annotations.py`: 원본 PNG를 그대로 포함하고 빨간 SVG 테두리와 아래 설명을 합성하는
  문서용 벡터 레이아웃 생성기. 스크린샷 픽셀을 수정하거나 글자를 덮어쓰지 않습니다.
- `images/01-*.svg` 등: 원본을 포함한 독립 SVG. 외부 네트워크나 절대 경로 없이 볼 수 있습니다.
  원본 스크린샷 SHA256을 SVG metadata에 포함했습니다.
- 편별 패키지 정리 후 Markdown은 함께 생성한 PNG를 사용합니다. PNG와 노션용 HTML ZIP은
  공통 `../export_lessons.py`로 재생성합니다.

화면을 다시 촬영했다면 해당 파일을 교체하고 위치 정보를 수정한 뒤 저장소 최상위에서
`python isaacsim_basic/01_object_physics/images/build_annotations.py`를 실행합니다. 그림마다 버튼과 테두리 위치를 다시 확인하세요.


## 2026-09-09 초기화·화면 배치 갱신

- 1·2편은 편집값을 유지하는 Stop 기반 초기화, 5편은 저장 기록을 보존하는 모형 초기화를 추가했습니다.
- 3·4·6편은 좌측 Perspective·우측 Front Camera와 색상 라인별 랜덤 큐브 리셋을 공통 사용합니다.
- 변경된 시작·조작·기록 화면을 실제 Isaac Sim 5.1 Docker에서 새로 캡처했습니다. 기본 도형·카메라 속성 메뉴 등 변경 없는 상세 화면은 기존 검증 캡처를 유지합니다.
- 원본 PNG는 수정하지 않고 SVG의 빨간 테두리와 별도 설명 영역으로 강조했습니다. 캡처에 마우스 커서는 포함되지 않으며 버튼·상태가 보이는지 확인했습니다.
- 새 캡처의 고유 폴더 이름은 제작 중 임시 실습 결과 예시이며, 학생은 자신의 실행 로그에 나온 경로를 사용합니다.
