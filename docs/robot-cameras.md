# 전방·손목 카메라

현재 두 카메라는 **모델 형상을 기준으로 잡은 임시 장착 위치**다.
실제 렌즈 중심·장착 방향·내부 광학 파라미터를 측정한 값이 아니다.
Isaac의 sim/scene/teleop 실행에서 생성하며 로봇의 물리 링크를 따라간다.
카메라 외형은 표시 전용이고 질량·충돌·관절을 추가하지 않는다.

## 위치와 방향

설정 파일: `isaac_sim/assets/cameras/mounts.json`.
각 translation의 단위는 m, 회전은 `quaternion_xyzw` 순서다.
변환은 **부모 링크 기준 렌즈 중심**이며 optical 좌표축은
**+X 오른쪽, +Y 아래, +Z 촬영 정면**이다.

| 이름 | 부모 링크 | 렌즈 중심 (m) | 임시 방향 |
|---|---|---|---|
| front | base_link | (0.110, 0.0017, -0.0063) | 베이스 +X 전방 |
| wrist | wrist_link | (-0.035, -0.045, 0.0181) | 기본 자세에서 전방·아래 25° |

전면 구멍 위치는 번들 `lekiwi_body_soarm_mount.stl`의 전방 형상으로 추정했다.
손목 카메라는 손목 위쪽의 임시 위치이며 현재 wrist_roll 이전 링크에 붙어 있다.
실제 장착물이 wrist_roll과 함께 회전하면 부모를 `gripper_link`로 바꾸고
해당 링크 기준 위치·회전을 다시 계산해야 한다.

카메라의 USD 경로는 해당 물리 링크 아래
`front_camera_optical_frame/Camera`, `wrist_camera_optical_frame/Camera`다.
optical frame의 원점과 렌즈 전면 중심, USD Camera의 원점은 일치한다.
USD 카메라는 -Z 정면·+Y 위를 사용하므로 Camera 자식에 X축 180° 변환을
적용한다. 입력 TF에 이 변환을 중복 적용하면 안 된다.
[USD 카메라 좌표 규약](https://openusd.org/release/api/class_usd_geom_camera.html).

## 확인과 추후 TF 반영

이미지를 다시 빌드한 뒤 `./lekiwi sim` 또는 `./lekiwi scene`을 실행한다.
뷰포트에서 `C`를 누르면 전체 → 전방 → 손목 시점으로 순환한다.
`T`는 전체 시점으로 돌아가 로봇 추적을 전환한다.
기존 `P` 캡처는 선택한 뷰포트를 저장한다.
두 카메라 동시 녹화·시간 동기화·데이터셋 기록은 아직 구현하지 않았다.
640×480의 4:3 광학 비율과 수평 화각 70°는 임시값이다.
뷰포트 캡처 픽셀 크기는 현재 창 크기를 따른다.

나중에 `soarm_base_link` 기준 TF를 제공할 때 다음을 함께 기록한다.

- 렌즈 중심의 translation과 quaternion, 길이 단위와 quaternion 순서.
- 정면 축과 위쪽 축. optical 규약과 다르면 먼저 변환한다.
- 손목 카메라 TF를 측정한 **동일 시점의 팔 관절각**과 실제 고정 링크.

기준을 S=soarm_base_link, 고정 링크를 L, optical frame을 C라고 하면
장착 변환은 `T_L_C = inverse(T_S_L(q)) × T_S_C`다.
손목 카메라를 S에 직접 고정하면 팔이 움직일 때 따라가지 않으므로,
측정 자세 q에서 L 기준으로 변환한 값을 저장한다.
front도 base_link 기준으로 변환한다. 현재 URDF의 base_link→soarm_base_link는
translation (0.019988279335, 0.001703025019, 0.052884) m, 회전 0이다.

수정한 설정은 기본 JSON에 반영하거나 호스트의 `data/cameras/mounts.json`에
별도로 저장하고 `.env`에 `LEKIWI_CAMERA_CONFIG=/data/cameras/mounts.json`을 지정한다.
후자는 이미지를 재빌드하지 않고 다음 실행부터 반영된다.
TF 연결 때문에 ROS 의존성을 추가할 필요는 없다. ROS/RViz 확인용 파일은
기존 `.local_ros/`에서 관리하며 Git·Docker에서 제외한다.

## 이번 변경의 검증 범위

- 호스트 자동 검사: `PYTHONPATH= PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests`
  → 165 passed, 7 skipped. 생략 항목은 호스트의 USD/Xacro 의존성 부재다.
- `/tmp`에 USD 25.11을 임시 설치해 카메라 좌표·추종·물리 설정 보존 검사 10개 통과.
  USD를 사용하는 코스·배포 관련 검사까지 112개 통과
  (Isaac 내장 셰이더 의존성 검사와 Xacro 재생성 검사는 이 실행에서 제외).
- Python/Bash 문법, Compose 설정, `git diff --check` 통과.
- 로컬 RViz에서 카메라 외형·TF 표시와 soarm_base_link 기준 정면 축 확인.
- Docker sudo 인증이 필요하여 변경 이미지 빌드, Isaac 렌더링과 C 키 시점 전환,
  실제 영상 가림·화각 검사는 아직 수행하지 못했다. 위 검사는 이를 대신하지 않는다.
