# 출처와 검증 범위

## 공식 자료

- [NVIDIA Isaac Sim 5.1 Core Nodes API](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/py/source/extensions/isaacsim.core.nodes/docs/index.html): `get_sim_time_at_time`으로 렌더 기준 시각을 물리 시각에 대응. 설치된 카메라 센서의 `_data_acquisition_callback`에서도 같은 변환 사용을 확인했습니다.

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

## 이전 검증 이력

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

연속 재생 수집으로 수정한 뒤 같은 날 추가 확인했습니다.

- 실제 Isaac Sim GPU 환경에서 가상 LeKiwi 팔을 움직이며 30프레임 자동 종료와 11프레임 수동 종료를 저장했습니다. 두 RGB는 원래 촬영 시각의 상태·명령에 연결됐습니다.
- 미리보기·기록·저장 중 PLAY/PAUSE 이벤트 0회, 마지막 영상 도착 후 UNSAVED, 사용자의 Pause 유지와 미완료 기록 Discard를 확인했습니다.
- 연속 수집한 2개 에피소드·41프레임의 LeRobot 변환·재열기·두 영상 디코딩 검사를 통과했습니다.
- 전체 자동 검사 234 passed, 1 skipped. 기존 스크린샷은 앞선 GUI 검증 실행이며, 추가 GPU 검증은 화면 없는 실행과 별도 GUI의 30프레임 자동 종료·Discard 확인입니다.

자세한 범위는 [전체 검증 기록](../VALIDATION.md)에 남겼습니다.
실제 리더 연결·기록의 후속 검증은 아래에 기록했습니다. 실측 카메라 TF 보정과 집기 품질은 별도 확인 대상입니다.
실제 노션 계정 가져오기, 학습과 정책 실행은 이 장의 제작 검증에 포함하지 않습니다.


## 파일 처리·일시정지 개선 검증 · 2026-09-08

- 무손실 PNG 압축 수준 1, 단일 작업 큐와 최대 4프레임 대기 제한을 적용했습니다. 파일 처리 코드는 Isaac Sim·GUI 객체를 사용하지 않습니다.
- 실제 GUI에서 기록 갱신율 약 24.4회/초, 저장 검사 중 최대 갱신 간격 약 43.3ms를 측정했습니다. 원본 90프레임의 시간·관측 연결·영상 무결성 검사를 통과했습니다.
- 실제 Space 입력의 PAUSE 이벤트는 0회였습니다. 별도 Pause/Play 복귀 검사에서 카메라 시각 경고도 0회였습니다.
- 전체 자동 검사 245 passed, 1 skipped. 느린 저장 장치·대기열 초과·쓰기와 검증 실패·종료·기존 저장본 보호를 포함합니다. 현재 단계는 성능 개선과 수집 경로 검증이며 장시간 실물 집기 품질 검증은 아닙니다.

## 5분 연속 수집과 저장 검사 메모리 개선 · 2026-09-08

- 실제 GUI에서 가상 팔을 움직이며 300초·9,000프레임(두 RGB 총18,000장)을 자동 종료·저장했습니다. 실제 수집 364.4초, 저장 검사 141.6초였으며 모든 프레임의 시간·관측 연결·이미지 무결성과 가상 목표 대응을 통과했습니다. 수집·검사 중 자동 PLAY/PAUSE 이벤트는 0회였습니다.
- 수집 평균 24.7회/초, 관측한 파일 대기열 최대 2프레임, RSS 약5,742~5,777MiB였습니다. 300회 갱신마다 읽은 메모리 표본이며 장시간 누수가 없다는 보장은 아닙니다. 드문 최대 화면 간격은 수집366ms·저장421ms로 남았습니다.
- 추가 1,800프레임 계측에서 저장 시작의 JSON 전체 읽기가 메모리 정리(GC)를 일으켜319ms 동안 실행을 막는 것을 확인했습니다. 저장 검사에서는 한 줄씩 읽고 직전 프레임만 보관하도록 바꿨습니다. 변환기에 필요한 전체 행 반환은 기존 기본 동작을 유지합니다.
- 변경 후 실제 GUI의 새 1,800프레임 기록·저장 검사를 통과했습니다. 수집 최대71.1ms, 저장 평균25.1회/초였습니다. 파일 검사 중 전체 행 누적은 제거했지만, Isaac Sim viewport 내부에서 시작된 메모리 정리342ms와 최대 화면 간격382ms가 한 번 남았습니다. 모든 순간 끊김을 제거한 결과로 해석하지 않습니다.
- 전체 자동 검사 250 passed, 1 skipped. 메모리 사용량 비교, 마지막 이미지 손상·마지막 관측 연결 오류·프레임 수 불일치·빈 기록도 검사했습니다. xacro 미설치 항목은 생략했습니다.
- 로컬 계측 자료: `data/diagnostics/course_long_20260908`, `course_spike_fixed_20260908`, `course_streaming_20260908`. 처음 추가한 계측 스크립트의 변수 충돌 실행은 실패 자료로 분리하고 성능 비교에서 제외했습니다.
- 이번 검사는 합성 입력의 가상 팔이며 실물 리더 USB는 열지 않았습니다. 이후 실물 연동 결과는 아래 별도 항목에 기록했습니다. 집기 품질 검증과 이 9,000프레임의 LeRobot 변환은 포함하지 않았습니다.

## 실물 SO101 리더 추종·기록 검증 · 2026-09-08

- 사용자가 전원·팔 지지·전원 차단 가능 상태를 확인한 뒤 기존 보정을 재사용했습니다. 연결 검사에서 6개 관절 모두 Torque_Enable=0과 보정 읽기 일치를 확인했습니다. 실제 리더에 토크 활성화나 목표 위치 명령을 보내지 않았습니다.
- 사용자가 실제 팔을 움직이며 정상 추종을 확인했고, 저장 데이터에서도 6개 관절의 입력 목표와 실제 관절값 변화를 확인했습니다. 베이스 명령은 전체 구간에서 0이었습니다. 관절 한계를 넘는 elbow_flex 목표는 기존 제한을 유지했습니다.
- Max seconds=0에서 수동 종료·Save를 진행했습니다. 1,291프레임·시뮬레이션 43.03초, 전방·손목 RGB 총 2,582장을 저장하고 모든 프레임의 시간·관측 연결·이미지 해시·해상도·디코딩 검사를 통과한 SAVED 상태를 확인했습니다.
- 로컬 원본은 `data/recordings/lekiwi.enj07n0j/episode.1dmz86zg`, 측정 기록은 `data/diagnostics/leader_verified_20260908`에 보관합니다. 생성 데이터와 로컬 보정 파일은 Git에서 제외합니다.
- 집기 작업을 수행하지 않아 success=false를 유지했습니다. 이 실물 입력 기록의 LeRobot 변환, 집기 품질, 실측 카메라 TF 보정과 학습·평가는 별도입니다. 간헐적인 약 0.38초 지연은 이번 단계의 잔여 제한으로 둡니다.

## 도면 TF 반영 후 확인

2026-09-08 기본 카메라 JSON에 SOARM base 기준 도면 치수를 반영하고 Docker 이미지를 다시 빌드했습니다.
실제 `record` GUI에서 두 RGB와 30프레임 저장을 확인했으며, 저장된 카메라 설정이 기본 JSON과 일치했습니다.
이후 기록 패널의 실제 화면 5장은 아래 재촬영본으로 교체했습니다. 이번 검증은 최종 실물 보정이나 집기 품질 검증을 의미하지 않습니다.
자세한 범위는 [전체 검증 기록](../VALIDATION.md)을 참고하세요.

## 실제 기록 화면 재촬영 · 2026-09-08

- 새 TF의 `./lekiwi record`에서 READY·RECORDING·UNSAVED·SAVED·DISCARDED 화면 5장을 다시 촬영했습니다.
- 기록 패널 높이를 늘려 두 RGB, 기록 시간, 버튼, 상태와 저장 경로를 함께 표시했습니다. 커서는 설명 대상 밖으로 이동했습니다.
- 30초 제한에서 3.30초·99프레임을 수동 종료하고 저장했습니다. 198개 RGB PNG와 프레임의 시간 대응·크기·SHA256, 기본 카메라 설정 일치를 확인했습니다.
- 베이스 +X 이동 약0.129 m와 마지막 10프레임의 베이스 정지 명령을 확인하고 주행 연습 과제 성공을 수동 표시했습니다.
  접촉 물리에 의한 잔류 움직임은 있으며, 정밀 정지나 집기 성공을 검증한 기록은 아닙니다.
- 추가 미저장 기록의 Discard 후 기존 저장본 200개 파일의 SHA256이 모두 유지됐습니다.
- 마지막 변환 터미널 이미지는 이전의 2개 에피소드·19프레임 검증 예시를 유지합니다. 이번 99프레임 기록의 변환 결과로 표시하지 않습니다.
- 로컬 촬영 기록: `data/recordings/lekiwi.gasxrsil/episode.39zf0ai1`, 검증 자료: `data/diagnostics/course_recapture_tf_20260908`.
