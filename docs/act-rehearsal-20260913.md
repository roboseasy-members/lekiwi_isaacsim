# ACT 학습·시뮬레이션 추론 실행 검사 · 2026-09-13

실제 SO101·베이스 움직임을 취득해 변환한 데이터로 학습 1회, 체크포인트 재로딩,
Isaac Sim 추론의 시작·정지·재시작을 확인했습니다. 학습 품질이나 집기 성공률을 평가한 결과는 아닙니다.

## 환경과 입력

- 서버: RTX 3070 Laptop GPU 8 GB, 드라이버 580.173.02, Isaac Sim 5.1.0 Docker.
- 실행 저장소: `/home/roboseasy/youn_ws/lekiwi_class_rehearsal`.
- 첫 학습·추론 확인은 회사 Wi-Fi에서 Tailscale 주소 `100.66.115.54`로 진행했습니다. 이후 모바일 데이터 핫스팟에서도 아래 추가 검사를 진행했습니다.
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
수업 화면에서의 상태 확인과 복구 절차는 [6장 ACT 추론](../isaacsim_basic/06_lekiwi_dataset/README.md#6-추론-스크립트로-같은-맵의-로봇-실행하기)을 따릅니다.

## 종료와 자동 검사

- `lesson train status`에서 SUCCEEDED와 종료 코드 0을 확인했습니다.
- `lesson stop`으로 추론 세션을 종료했습니다. 학습 결과와 원본 데이터는 보존했습니다.
- 관련 자동 검사: `tests/test_act_workflow.py`, `tests/test_web_classroom.py` 56개 통과.
- 첫 학습·추론 검사 당시 수정 범위는 교재·검증 기록과 07번 학생 파일의 설명 문자열입니다. 학습·추론 처리 코드는 변경하지 않았습니다.
- 변경 문서 링크·Python 문법·diff와 갱신한 6장 Notion ZIP을 검사했습니다.

## 모바일 데이터 핫스팟 추가 검사

본 노트북은 회사 Wi-Fi, 서버 역할의 서브 노트북은 휴대폰 핫스팟에 연결했습니다.
처음에는 핫스팟을 사용해도 두 노트북의 공인 IP가 같았습니다. 휴대폰의 Wi-Fi를 끄고
모바일 데이터만 사용한 뒤 서로 다른 공인 IP를 확인했습니다. 핫스팟 이름이나 사설 IP가
다르다는 사실만으로 다른 인터넷 회선이라고 판단하지 않았습니다.

- 본 노트북: 회사 인터넷, Tailscale `100.76.197.70`.
- 서브 노트북: 모바일 인터넷, Tailscale `100.66.115.54`.
- 검사 시작과 종료 시 서로 다른 공인 IP를 확인했고, Tailscale 경로는 `direct`였습니다.
- 초기 ping 5회는 67·90·59·128·960 ms, 종료 시 3회는 117·33·459 ms였습니다. 짧은 표본에서도 지연 변동이 있었습니다.
- 기존 `act_rehearsal_20260913_01` 모델을 재사용해 `lesson infer`로 실행했습니다. 추가 학습이나 실제 리더암 조작은 하지 않았습니다.

| 확인 항목 | 핫스팟에서 관측한 결과 |
|---|---|
| ACT 시작·시간 제한 | R → RUNNING → FINISHED, 시뮬레이션 분량 2초 |
| Space / F8 | 실행 중 정지 / 장면 초기화 PASS와 READY 전환 |
| 일시정지·Play | 일시정지에서 STOPPED, Play 후에도 정지 유지, R로 재실행 완료 |
| 영상 연결 종료·재접속 | 클라이언트 새로고침으로 연결 종료 → STOPPED, 같은 주소로 재접속 후에도 정지 유지 |
| 재접속 후 R | RUNNING → FINISHED, 모델 로그와 추론 상태 기록에 요청 실패 없음 |
| 연속 영상 관찰 | 1280×720, 약 124초 동안 63회 관찰에서 영상 준비 상태 유지, 예기치 않은 연결 종료 없음 |
| 영상 갱신 | 프레임 카운터 증가 2,163, 누락 프레임 카운터 증가 8, 관측한 최대 화면 갱신 간격 약 0.4초 |

화면 갱신 간격은 입력부터 화면 반응까지의 전체 지연을 측정한 값이 아닙니다.
재접속 검사는 클라이언트 연결을 의도적으로 종료한 경우이며, 장시간 모바일 회선 단절을 재현한 검사는 아닙니다.

첫 실행은 영상 연결 준비 전에 `carb::cpp::bad_optional_access`로 종료됐습니다.
스택에 `libcarb.profiler-cpu.plugin.so`가 나타났고, 종료 후 중복 실행 여부와 GPU·메모리·디스크를
점검했습니다. 코드·이미지·설정을 바꾸지 않고 한 차례 재시작한 실행에서 위 검사를 마쳤습니다.
당시에는 원인 미확인으로 기록했으며, 아래 추가 조사에서 CPU 시간 계산 문제로 원인을 좁혔습니다.

- 성공 세션: `data/web_classroom/sessions/inference.aj4g4e9c/run.log`.
- 성공 모델 로그: `data/policy/act.wq782xdo/policy.log`.
- 최초 실패 세션: `data/web_classroom/sessions/inference.at96n7f1/run.log`.
- 본 노트북의 관측 JSON·원본 화면 캡처·오류 로그: `data/diagnostics/act_hotspot_20260913/` (Git 제외).
- 검사 후 `lesson stop`과 실행 컨테이너 조회로 ACT·시뮬레이터 종료를 확인했습니다.
- 이번 추가 검사는 실행 코드 변경 없이 진행했습니다. 검증 기록만 갱신했습니다.

## 시작 오류 원인 추가 확인

서버 CPU 코어 간 시간값(TSC)이 어긋난 상태와 Carbonite 206.6 CPU 프로파일러의
시간 계산 실패 처리가 이번 시작 오류에 부합합니다. 다음 세 가지 독립적인 근거를 확인했습니다.

1. 서버 부팅 로그에 `TSC warp between CPUs`와 `Marking TSC unstable`이 있습니다.
   Linux는 TSC를 제외하고 `hpet` 타이머를 사용 중입니다.
2. 별도 진단 프로그램에서 자신의 실행 CPU만 바꾸며 시간값을 읽었습니다. 47개 전환 표본 중
   2개에서 TSC가 역행했습니다. 해당 표본에서도 운영체제의 단조 시간은 정상 증가했습니다.
   시스템 시간·커널 설정·다른 프로세스의 CPU 배치는 변경하지 않았습니다.
3. 실패 로그의 라이브러리 주소를 실제 서버 이미지의 바이너리와 대조했습니다.
   예외 지점 `0x25736`은 TSC 주파수를 계산하다 실패하는 경로이며, 예외 다음 주소
   `0x2573b`가 원래 스택의 `0x24e90 + 0x8ab`와 일치합니다. 설치된 SDK 헤더도
   계산 실패 시 비어 있는 결과에 `.value()`를 호출하는 형태였습니다.

NVIDIA는 같은 종류의 TSC 계산 실패 시 CPU 프로파일러가 종료되는 문제를
Carbonite 210.1.1의 `OMPE-80586`에서 수정했다고 기록합니다.
현재 이미지의 Carbonite는 206.6입니다.
근거: [NVIDIA 변경 기록](https://docs.omniverse.nvidia.com/kit/docs/carbonite/latest/CHANGES.html),
[206 계열의 TSC 계산 코드](https://docs.omniverse.nvidia.com/kit/docs/carbonite/206.0/api/program_listing_file_carb_clock_TscClock.h.html).

실패·성공 실행의 시작 인자와 적용 설정 파일 목록은 같았습니다. 오류는 렌더러와 WebRTC 준비 전
약 80 ms 시점에 발생했으며, 핫스팟 연결 실패로 분류할 근거는 없습니다.
TSC가 어긋난 근본 이유가 펌웨어·부팅 상태·커널 중 무엇인지는 아직 구분하지 못했습니다.

| 추가 검사 | 결과 |
|---|---|
| 기존 ACT 실행 설정으로 시작·종료 3회 | 3회 모두 모델과 시뮬레이션 READY. 간헐 오류가 해결됐다는 의미는 아님 |
| 일회성 NVTX 우회 시작 | 약 36초 후 READY |
| NVTX 실행 영상·조작 | 1280×720 영상, 가상 베이스 전진·정지, F8 초기화 PASS |
| 실제 로드된 라이브러리 | NVTX 모듈 로드, CPU 프로파일러 모듈 미로드 |

우회 검사는 `./lekiwi sim --/app/profilerBackend=nvtx --/app/profileFromStart=false`에
기존 WebRTC 환경 변수를 지정해 진행했습니다. NVTX는 Kit에서 지원하는 프로파일러입니다.
근거: [Kit 프로파일링 설정](https://docs.omniverse.nvidia.com/kit/docs/kit-manual/107.3.1/guide/profiling.html).
이 검사는 일반 시뮬레이션의 일회성 실행이며, 우회 옵션으로 ACT 실행이나 전체 단원을 검증한 것은 아닙니다.

위 일회성 조사 단계에서는 실행 코드·이미지·BIOS·커널 설정을 변경하지 않았습니다. 실제 USB나 모터도 조작하지 않았습니다.
진단 로그·관측 JSON·화면 캡처는 본 노트북의 `data/diagnostics/isaac_startup_20260913/`에 보존했습니다.

## 공통 실행기 반영

`docker/sim-entrypoint.sh`에서 Isaac Sim을 사용하는 실행은 `isaac_sim/sim_launcher.py`를
거칩니다. `app_runtime.install_profiler_defaults()`가 첫 `SimulationApp`에 NVTX와
`profileFromStart=false` 기본값을 적용한 뒤 SDK 클래스를 원래대로 복구합니다.
학생 실행기가 명령 인자를 다시 설정하더라도 적용되며, 녹화 옵션과 명시적으로 선택한 프로파일러는 보존합니다.
자산 목록 검사·URDF 생성처럼 Isaac Sim 앱을 만들지 않는 명령은 기존 실행 경로를 유지합니다.

장별 접속 검사에서는 영상 종료 직후 다음 실습을 시작할 때 `Address already in use`도 발견했습니다.
실행 중인 영상 서버가 없어도 TCP `TIME_WAIT` 때문에 포트 사전 검사가 실패하는 현상을 재현했습니다.
`tools/remote_classroom/main.py`의 검사 소켓에 `SO_REUSEADDR`를 적용했으며,
실제 LISTEN 서버는 계속 차단하고 종료된 연결의 대기 상태만 허용하는 자동 검사를 추가했습니다.

- 자동 검사: 공통 실행·원격 통신·ACT·수업 실행·배포·학생 파일 관련 206개 통과.
  로컬 Python에 USD 모듈이 없는 검사 1개는 건너뛰었으며, 아래 별도 GPU 검사를 수행했습니다.
- 기존 빈 편집 화면에는 자동 장면 생성 함수가 없으므로 해당 파일의 import 검사 조건을 교재 목적에 맞췄습니다.
- 실제 GPU `basic-test`: 중력·접촉·질량·마찰·반발력, 관절 목표·제한, 2~5장 API 검사 통과.
- 실제 GPU `recording-test`: 관절 180프레임 기록·재생 검사 통과. 기초 검사 내 학생 코드 재생 오차도 0 rad였습니다.
- 실제 GPU `camera-test`: 두 카메라와 상태·행동 60프레임 저장·검사 통과.
- 서버에 없던 기존 빈 화면 파일을 추가하고 4·5장 주석을 현재 교재와 맞췄습니다.
- 서버 `lekiwi-sim:0.1.0` 이미지: `sha256:901ef049da64217fc62ec3212885fb44d7836e44bbd9d5255a9c7537bc5e524b`.
  GPU 검사는 직전 이미지 `6bfdaebb…`에서 수행했으며, 최종 이미지와 공통 실행 코드는 같습니다.
  이후 이미지 변경은 위 빈 화면 파일 추가와 4·5장 주석 동기화입니다.

### 최종 이미지에서 학생 실행·ACT 확인

학생용 `lesson run`과 `lesson infer`에 프로파일러 옵션을 추가하지 않고 검사했습니다.
빈 화면과 각 장의 기본 실습을 차례로 시작·종료했으며, 모든 실행에서 READY와
1280×720 영상 프레임 증가를 확인했습니다. 1장에서 2장으로 바로 전환하는 경우를 포함해
수정 후 장별 전환에서 포트 사전 검사 오류가 재발하지 않았습니다.

| 실행 | 서버 세션 (`data/web_classroom/sessions/` 아래) | 결과 |
|---|---|---|
| 마우스 실습용 빈 화면 | `lesson.a2bf5k2l` | READY·영상 수신 |
| 1장 물체·물리 | `lesson.kheblzk4` | READY·영상 수신 |
| 2장 | `lesson.epsasodx` | READY·영상 수신 |
| 3장 | `lesson.dn5q9ejo` | READY·영상 수신 |
| 4장 | `lesson.doyz0h3z` | READY·영상 수신 |
| 5장 | `lesson.y636jv5i` | READY·영상 수신 |
| 6장 | `lesson.ie5jybc8` | READY·영상 수신 |
| ACT 추론 | `inference.6lw9srv0` | READY·영상 수신·아래 조작 검사 |

8개 실행 모두 실제 프로세스의 라이브러리 목록에서 NVTX 프로파일러 로드와
CPU 프로파일러 미로드를 확인했습니다. 로그에도 `LEKIWI_RUNTIME profiler_backend=nvtx`가 있습니다.
이번 단원 검사는 각 장의 기본 실행 경로와 영상에 대한 검사이며, 교재의 모든 마우스 조작을 다시 수행한 것은 아닙니다.

ACT는 기존 `act_rehearsal_20260913_01` 체크포인트를 `cuda`, `seconds=2`로 재사용했습니다.
모델 로그는 `data/policy/act.x7dqbbs3/policy.log`이며, 추가 학습이나 실제 장비 조작은 하지 않았습니다.

| ACT 확인 항목 | 관측 결과 |
|---|---|
| R 시작·시간 제한 | RUNNING → FINISHED |
| Space / F8 | 실행 중 STOPPED / 장면 초기화 PASS와 READY |
| 일시정지·Play | 일시정지에서 STOPPED, Play 후에도 정지 유지 |
| 영상 종료·재접속 | 실행 중 STOPPED, 1280×720 영상 복구 후에도 정지 유지 |
| 재접속 후 R | RUNNING → FINISHED, 모델 요청 오류 없음 |

코드·서버 이미지에 우회 설정을 반영하고 해당 경로의 실행 검사를 마쳤습니다.
이는 문제가 발생한 CPU 프로파일러 경로를 피한 결과이며, 서버 CPU의 TSC 불일치를 고친 것은 아닙니다.
검사 후 `lesson stop`과 편집기 정상 종료를 수행했으며, 서버에 관련 컨테이너와 시뮬레이션 프로세스가 남아 있지 않은 것을 확인했습니다.
서버의 공통 실행·포트 검사 파일 4개는 본 노트북의 수정본과 해시가 일치합니다.
검사 결과 JSON·빌드 로그·화면 캡처는 본 노트북의 `data/diagnostics/nvtx_rollout_20260913/`에 보존했습니다.

## 남은 확인

- 서버 TSC 불일치의 근본 원인 및 재부팅 이후 상태 확인.
- 배정된 15쌍 장비에서 동시 접속·영상·조작과 장시간 수업 안정성.
- 충분한 성공 시연으로 본 학습을 진행한 뒤 과제 성공률 평가.
- 새 교육용 PC에서 신규 설치·드라이버 준비부터 시작하는 전체 수업 리허설.

이 문서는 한 쌍의 준비된 장비에서 확인한 실행 결과입니다. 여러 학생의 성능이나 실제 로봇의 정책 실행을 검증한 것으로 확대하지 않습니다.
