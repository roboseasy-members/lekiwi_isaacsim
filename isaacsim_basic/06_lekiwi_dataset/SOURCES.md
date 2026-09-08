# 출처와 검증 범위

## 공식 자료

- [NVIDIA Replicator 동기 캡처](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/replicator_tutorials/tutorial_replicator_getting_started.html): 타임라인 일시정지와 delta_time=0으로 같은 상태의 두 render product를 캡처.

- [NVIDIA Isaac Sim 5.1 카메라 센서](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/sensors/isaacsim_sensors_camera.html): USD Camera의 render product에서 RGB를 읽는 방식.
- [NVIDIA 이미지 위젯](https://docs.omniverse.nvidia.com/kit/docs/omni.kit.documentation.ui.style/1.0.7/buttons.html): ByteImageProvider와 ImageWithProvider로 실제 센서 미리보기 표시.
- [NVIDIA Window API](https://docs.omniverse.nvidia.com/kit/docs/omni.ui/latest/omni.ui/omni.ui.Window.html): Stage와 같은 영역에 창 도킹.
- [Hugging Face LeRobotDataset v3](https://huggingface.co/docs/lerobot/main/lerobot-dataset-v3): 에피소드·Parquet·영상 구조와 finalize 절차.
- [LeRobot 데이터셋 API](https://huggingface.co/docs/lerobot/main/api/datasets): create, add_frame, save_episode, finalize, 다시 읽기.

온라인 문서의 main/latest는 변경될 수 있습니다. 구현에는 이 저장소 Docker의 Isaac Sim 5.1.0과 LeRobot 0.6.1에 실제 설치된 API를 확인했습니다.

## 프로젝트에서 추가한 부분

기존 LeKiwi 주행·팔 제어 경로에 두 카메라 수집을 선택적으로 연결했습니다.
원본 PNG·JSONL·manifest, 성공 표시, 누락·동기화·파일 무결성 검사, 로컬 LeRobot 변환은 이 교재를 위한 프로젝트 코드입니다.
Record·Save·Discard 버튼은 Isaac Sim의 기본 메뉴가 아닙니다.

## 검증 범위

2026-09-08 제작 PC에서 다음 항목을 확인했습니다.

- 실제 GUI에서 두 RGB 미리보기, Stage 옆 자동 배치, 기록·종료·성공 표시·저장·버리기를 확인했습니다.
- 키보드 전진·정지 기록 11프레임과 연습 기록 8프레임을 저장했습니다. 첫 기록의 베이스 +X 이동은 약 0.036 m였고 마지막 속도 명령은 0입니다.
- 모든 원본 프레임의 1/30초 간격, 두 render reference 일치, 관측 연결, RGB 크기·SHA256 검사를 통과했습니다.
- 2개 에피소드·19프레임의 LeRobot 변환·재열기·두 영상 디코딩 검사를 통과했습니다.
- success-only 변환은 성공으로 표시한 1개 에피소드·11프레임만 선택했습니다.
- 전체 자동 검사 215 passed, 1 skipped. xacro 미설치로 URDF 재생성 검사는 건너뛰었습니다.
- 수집 시간 설정을 추가한 실제 Isaac Sim 화면 5장으로 갱신했습니다. 변환 터미널 화면은 앞서 검증한 2개 에피소드·19프레임의 별도 실행 결과입니다.
- 최대 120초 설정에서 13프레임을 수동 종료·저장하고 manifest 설정값을 검증했습니다. 1초 설정은 정확히 30프레임에서 UNSAVED, 0 설정은 11프레임에서 수동 종료되는 것을 GUI로 확인했습니다.
- 시간 설정 변경 후 관련 자동 검사 60 passed, 1 skipped. 30초를 넘는 기록, 지정 경계 자동 종료, 무제한, 설정 고정과 수동 종료를 검사했습니다.

자세한 범위는 [전체 검증 기록](../VALIDATION.md)에 남겼습니다.
실측 카메라 TF 보정과 실제 리더 연결·집기 시연은 별도 확인 대상입니다.
실제 노션 계정 가져오기, 학습과 정책 실행은 이 장의 제작 검증에 포함하지 않습니다.
