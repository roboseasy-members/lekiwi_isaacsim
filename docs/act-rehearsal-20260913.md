# ACT 학습·시뮬레이션 추론 실행 검사 · 2026-09-13

실제 SO101·베이스 움직임을 취득해 변환한 데이터로 학습 1회, 체크포인트 재로딩,
Isaac Sim 추론의 시작·정지·재시작을 확인했습니다. 학습 품질이나 집기 성공률을 평가한 결과는 아닙니다.

## 환경과 입력

- 서버: RTX 3070 Laptop GPU 8 GB, 드라이버 580.173.02, Isaac Sim 5.1.0 Docker.
- 실행 저장소: `/home/roboseasy/youn_ws/lekiwi_class_rehearsal`.
- 이번 학습·추론 확인은 회사 Wi-Fi에서 Tailscale 주소 `100.66.115.54`로 진행했습니다.
- 입력: `data/datasets/tailscale-teleop-check-20260913`, 1에피소드·900프레임·30 FPS.
- 원본 취득·변환 검사는 [앞선 통신·취득 기록](tailscale-teleop-check-20260913.md)을 참고합니다.
- 두 RGB 카메라와 9개 상태·행동을 사용했고, 카메라 설정은 변환본의 `recording_report.json`에서 읽었습니다.
- 실제 리더 입력 프로그램은 종료한 상태로 검사했습니다. 이번 단계에서는 USB를 열거나 실제 모터를 조작하지 않았습니다.

## 학생 스크립트에서 학습 시작

브라우저 편집기 컨테이너 안에서 `06_train_act.py`를 읽고 아래 설정으로 `main()`을 호출했습니다.
기본 설정 파일은 보존하고 검사 실행에만 값을 지정했습니다. 실제 `lesson train start`와
서버 작업 관리, 공식 `lerobot-train`, 결과 상태 조회를 거쳤습니다.

| 설정 | 검사 값 |
|---|---|
| dataset_name | `tailscale-teleop-check-20260913` |
| run_name | `act_rehearsal_20260913_01` |
| steps / batch_size / num_workers | `1 / 1 / 0` |
| device / pretrained_backbone | `cuda / False` |

- 학습 작업: `data/web_classroom/training/train.umqxpyco`.
- 900프레임을 읽고 1회 학습을 마쳤습니다. 로그의 손실은 11339.373으로 유한한 값입니다.
- `LEKIWI_ACT_TRAIN result=PASS`, `LEKIWI_TRAIN_JOB result=PASS`를 확인했습니다.
- 결과: `data/outputs/act_rehearsal_20260913_01/`.
- `train/checkpoints/last/pretrained_model`은 `000001/pretrained_model`을 가리킵니다.
- 모델 가중치·ACT 설정·전처리·후처리와 `lekiwi_policy.json`, `training_result.json`을 저장했습니다.
- `pretrained_backbone=False`인 1회 실행 모델입니다. 손실값을 수렴이나 작업 성능의 근거로 사용하지 않습니다.

## 저장 모델로 추론

같은 편집기에서 `07_infer_act.py`의 실행 설정을 위 `run_name`, `checkpoint='last'`,
`device='cuda'`, `seconds=2`로 지정했습니다. `lesson infer`가 모델과 시뮬레이터를 시작했습니다.
모델 로딩에는 저장한 가중치와 전·후처리기를 사용했으며 Hub 접속 없이 준비됐습니다.

- 실습 로그: `data/web_classroom/sessions/inference.io2mltfk/run.log`.
- 모델 로그: `data/policy/act.36wa367d/policy.log`.
- `LEKIWI_ACT_POLICY result=READY`, `lesson status`의 READY와 1280×720 영상 수신을 확인했습니다.

| 확인 항목 | 관측 결과 |
|---|---|
| R 시작·시간 제한 | RUNNING → FINISHED. 30 FPS 기준 2초 분량의 모델 행동을 처리 |
| Space | 실행 중 STOPPED로 전환 |
| F8 | 실행 중 장면 초기화 PASS, 추론은 READY로 전환 |
| 일시정지·Play | 일시정지에서 STOPPED. Play만 눌렀을 때 정지 유지 |
| 영상 연결 종료 | 실행 중 연결 종료를 감지하고 STOPPED |
| 영상 재접속 | 같은 Tailscale 주소로 영상 복구, 추론 정지 유지 |
| 재접속 후 R | 다시 RUNNING → FINISHED. 관측 순서·모델 응답 오류 없이 완료 |

`seconds`는 처리한 시뮬레이션 분량입니다. 모델 계산 중 물리 시간을 멈추므로 실제 기다리는 시간과 다릅니다.
수업 화면에서의 상태 확인과 복구 절차는 [6장 ACT 추론](../isaacsim_basic/06_lekiwi_dataset/README.md#68-act-추론-스크립트)을 따릅니다.

## 종료와 자동 검사

- `lesson train status`에서 SUCCEEDED와 종료 코드 0을 확인했습니다.
- `lesson stop`으로 추론 세션을 종료했습니다. 학습 결과와 원본 데이터는 보존했습니다.
- 관련 자동 검사: `tests/test_act_workflow.py`, `tests/test_web_classroom.py` 56개 통과.
- 수정 범위는 교재·검증 기록과 07번 학생 파일의 설명 문자열입니다. 학습·추론 처리 코드는 변경하지 않았습니다.
- 변경 문서 링크·Python 문법·diff와 갱신한 6장 Notion ZIP을 검사했습니다.

## 남은 확인

- 배정된 15쌍 장비에서 동시 접속·영상·조작과 장시간 수업 안정성.
- 충분한 성공 시연으로 본 학습을 진행한 뒤 과제 성공률 평가.
- 새 교육용 PC에서 신규 설치·드라이버 준비부터 시작하는 전체 수업 리허설.

이 문서는 한 쌍의 준비된 장비에서 확인한 실행 결과입니다. 여러 학생의 성능이나 실제 로봇의 정책 실행을 검증한 것으로 확대하지 않습니다.
