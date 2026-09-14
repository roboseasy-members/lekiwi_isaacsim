# Tailscale 원격 조작·수집 검증 기록 (2026-09-13)

2026-09-13, 본 노트북은 회사 Wi-Fi `roboseasy`, 서버 역할의 서브 노트북은
휴대폰 모바일 데이터 핫스팟 `YSJ`에 연결한 상태에서 캡처했습니다.
공식 WebRTC 클라이언트가 받은 1280×720 영상과 클라이언트 창을 그대로 저장한 원본입니다.
화면의 서버 주소 `100.66.115.54`는 이번 검증 장비의 주소이며 학생은 자신의 배정 서버 주소를 사용합니다.

| 원본 파일 | 해당 단원에서 확인할 단계 |
|---|---|
| [01-client-server-address.png](../isaacsim_basic/00_env_setting/images/screenshots/01-client-server-address.png) | Server에 서버의 Tailscale 주소를 넣고 해상도를 선택한 뒤 Connect |
| [02-leader-following.png](../isaacsim_basic/04_teleoperation/images/screenshots/11-remote-leader.png) | 리더 연결·보정 확인 후 영상 창에서 R 입력, `ARM Following leader` 확인 |
| [03-base-turn.png](../isaacsim_basic/04_teleoperation/images/screenshots/12-remote-base.png) | 베이스 회전 후 로봇 방향과 전방 카메라 화면의 변화 확인 |
| [04-recording-active.png](../isaacsim_basic/06_lekiwi_dataset/images/screenshots/11-remote-recording.png) | F5 입력 후 `REC / RECORDING`과 프레임 증가를 직접 확인 |
| [05-recording-not-saved.png](../isaacsim_basic/06_lekiwi_dataset/images/screenshots/12-remote-unsaved.png) | 30초 제한으로 기록이 끝난 상태. `STOPPED / NOT SAVED`는 아직 저장 완료가 아님 |
| [06-recording-saved.png](../isaacsim_basic/06_lekiwi_dataset/images/screenshots/13-remote-saved.png) | F7 연습 저장 후 `SAVED`, 30초·900프레임 확인 |
| [07-front-wrist-cameras.png](../isaacsim_basic/06_lekiwi_dataset/images/screenshots/14-remote-cameras.png) | C로 왼쪽 화면을 손목 카메라로 전환. 왼쪽 손목·오른쪽 전방 영상 확인 |

## 검증 메모

- 실제 SO101 리더암의 기존 보정값을 재사용했고 연결·종료 시 6개 모터의 토크 OFF를 확인했습니다.
- 사용자가 팔·집게 추종을 확인했습니다. 베이스의 전진·회전과 입력 해제 후 정지는 화면과 서버 로그로 확인했습니다.
- 움직임이 담긴 원본은 서버의 `data/recordings/lekiwi.36tndw9q/episode.cj2vtqrq`입니다.
  `manifest.json`에서 `complete=true`, `success=false`, `fps=30`, `frames=900`을 확인했습니다.
  팔 관절·베이스 상태와 행동 값, 베이스 위치 변화가 기록돼 있습니다.
- 앞서 저장한 `episode.gc0ok6fx`의 446프레임은 정지 상태의 기록 검사입니다.
  팔·베이스 움직임을 저장했다는 증거로 사용하지 않습니다.
- 900프레임 기록을 서버의 `data/datasets/tailscale-teleop-check-20260913`으로 변환했습니다.
  `LeRobotDataset`으로 다시 열어 1개 에피소드·900프레임, 상태·행동 각각 9개 값,
  전방·손목 영상 각각 640×480·30fps, `codebase_version=v3.0`을 확인했습니다.
  원본 이미지 1,800개의 해시·해상도·촬영 시각과 프레임 연속성을 검사했고,
  변환 결과의 처음·중간·마지막 상태/행동과 두 영상 디코딩 검사를 통과했습니다.
  결과는 해당 데이터셋의 `recording_report.json`에 남아 있습니다.
- 네트워크 응답 대기가 50ms에서 끝나는 문제를 재현하고, 요청 전체의 200ms 한도까지 기다리도록 수정했습니다.
  통신·SO101 관련 자동 검사 90개를 통과했고 본 노트북의 리더 이미지에 반영했습니다.
- 수정 후에도 핫스팟에서 500ms를 넘는 입력 공백과 추종 해제가 관측됐습니다.
  캡처는 해당 순간의 동작 확인이며 장시간 안정성이나 15쌍 동시 수업의 통과 증거는 아닙니다.
  위 실제 장비 검증 당시에는 200ms를 넘은 응답 거부, 500ms 입력 단절 시 정지, 복구 후 R 재활성화 조건이었습니다.

## 이후 통신 복구 구현

- 0장은 기본 연결 화면만 사용하고, 리더·베이스 캡처는 4장, 기록 캡처는 6장에 보관합니다.
- 원격 입력 500ms 공백에서 정지하고, 마지막 유효 입력부터 2초 이내 같은 연결의 새 표본 3개를 확인하면 팔 추종을 재개합니다.
- Space·화면 연결 종료·초기화·긴 단절은 자동 재개를 취소합니다. 베이스 키는 초기화합니다.
- 기록 중 단절은 해당 에피소드를 마감합니다. F7 연습 저장 또는 F10 두 번 폐기 후 새 기록을 시작합니다.
- 이 변경은 자동 검사로 검증합니다. 위 사진·900프레임 데이터는 변경 전 캡처이며 새 기능의 핫스팟 실기 검증 증거가 아닙니다.

## 교재 편집 시 유의점

- 리더암 연결은 토크를 해제하므로, 실제 리더 장치인지와 팔 지지·전원 차단 준비를 먼저 확인합니다.
- 녹화 키를 눌렀다는 사실만으로 기록 시작을 표시하지 않습니다. `REC`와 프레임 증가를 확인합니다.
- F6 종료와 F7 저장을 구분하고, 저장 중에는 완료를 기다린 뒤 다음 에피소드를 시작합니다.
- 각 장의 `images/screenshots/`에는 캡처 원본을 보존합니다. 교재용 SVG에는 원본 해시와 빨간 강조 박스를 넣고 PNG로 내보냅니다.
- 계정 인증 화면, 로그인 링크, 접속 문구와 비밀번호는 캡처에 포함하지 않았습니다.

## 복구 구현의 자동 검사 결과

- 통신·리더·기록 패널·화면 표시 관련 검사: 147개 통과.
- 최종 회귀 검사: 318개 통과, 1개 건너뜀. 로컬 Python에 `pxr.UsdUtils`가 없어 USD 자산 검사 1개를 실행하지 못했습니다.
- 실제 로컬 UDP 소켓에서 입력 공백 → 정지 → 같은 송신기의 새 표본 3개 → 재개를 확인했습니다.
- 중단된 기록을 실제 파일로 연습 저장한 뒤 `complete=true`, `success=false`, 프레임 수·시간 연결을 재검사했습니다.
- 변경 Python 문법, `git diff --check`, 0·4·6장 Markdown 링크와 Notion ZIP 이미지 포함 검사를 통과했습니다.
- 초기 자동 검사 이후 서버·리더 Docker 이미지에 적용하고 아래의 실제 통신 검사를 진행했습니다.

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q -rs \
  tests/test_remote_classroom.py tests/test_so101_teleop.py \
  tests/test_recording_panel.py tests/test_recording_overlay.py \
  tests/test_episode_data.py tests/test_episode_worker.py \
  tests/test_scene_tools.py tests/test_drive_controls.py tests/test_drive_hotkeys.py \
  tests/test_act_workflow.py tests/test_classroom.py tests/test_web_classroom.py \
  tests/test_deployment.py
```

## Docker 반영 후 실제 통신 검증

본 노트북 `roboseasy` Wi-Fi ↔ 서버 노트북 `YSJ` 모바일 핫스팟 구성에서 Tailscale 직접 연결로 검사했습니다.
서버는 `/home/roboseasy/youn_ws/lekiwi_class_rehearsal`의 `session.5vel3jwm`을 사용했습니다.
시험 입력 검사를 먼저 마친 뒤 실제 SO101 리더를 연결했습니다. 사용자가 팔·집게 추종을 확인했습니다.

| 검사 | 실행 내용 | 확인 결과 |
|---|---|---|
| 짧은 단절 | 시험 송신 1.3초 중단 | RECONNECTING을 표시하고 R 없이 추종 복구 |
| 긴 단절 | 시험 송신 4초 중단 | 입력 복구 후에도 정지, R 입력 후 재개 |
| 재개 취소 | 짧은 단절 중 Space | 입력 복구 후에도 정지, R 필요 |
| 베이스 키 | W를 누른 채 단절·복구 후 자동 반복 입력 | 정지 유지, 키 해제 후 새 W에서만 전진 |
| 기록 중단 | 수집 중 시험 송신 중단 | 21프레임에서 UNSAVED, F9 차단, F7 연습 저장 |
| 영상 재접속 | 새 기록 중 클라이언트 연결 종료·같은 주소로 재접속 | 16프레임에서 UNSAVED, 팔 정지 유지, F7 저장·R 재개 |
| 실제 리더의 짧은 통신 단절 | 노트북→해당 서버 UDP 49101만 1.1초 차단 | 리더 프로그램 유지, 같은 연결로 R 없이 추종 복구 |
| 실제 리더의 긴 통신 단절 | 같은 UDP 입력을 3.5초 차단 | 정지 유지, 통신 복구 확인 후 R로 재개 |

실제 패킷 차단 규칙은 이번 서버의 리더 입력만 대상으로 추가했고, 각 검사 후 해당 규칙을 제거했습니다.
영상과 SSH를 전달하는 통신은 유지했습니다. 전체 Wi-Fi를 껐다 켜는 검사와 구분합니다.

첫 실제 패킷 차단 검사에서 소켓의 `EPERM` 오류가 리더 프로그램을 종료시키는 문제를 재현했습니다.
소켓의 `EPERM`·`EACCES`는 다음 전송 주기에 재시도하도록 수정하고 리더 이미지를 다시 빌드한 뒤 위 검사를 통과했습니다.
USB 읽기의 동일 오류는 자동 재시도하지 않는 회귀 검사도 포함했습니다. 최초 실패 종료 시 6개 모터의 토크 OFF를 확인했습니다.

이후 영상 수신이 실제로 끊겼을 때 서버 실행과 팔·베이스 정지 상태를 확인했습니다.
클라이언트의 같은 Tailscale 주소로 재접속해 영상 수신을 복구했고, R 재개 후 사용자가 팔·집게 추종을 다시 확인했습니다.
연결이 끊긴 원인 자체는 이 검사만으로 확정하지 않았습니다.
실기 종료 시 리더 프로그램은 정상 종료했고, 6개 모터 모두 `Torque_Enable=0`을 직접 읽어 확인했습니다.

새 교재 캡처는 다음과 같습니다. 화면의 상태를 직접 확인한 사진만 사용합니다.

- [짧은 단절의 자동 복구 대기](../isaacsim_basic/04_teleoperation/images/13-network-reconnecting.png): 시험 입력으로 확인한 실제 송출 화면.
- [긴 단절 이후 R 필요](../isaacsim_basic/04_teleoperation/images/14-network-manual-resume.png): 실제 리더 입력의 패킷 차단 후 화면.
- [기록 중단·저장 선택](../isaacsim_basic/06_lekiwi_dataset/images/15-network-recording-interrupted.png): 21프레임에서 통신으로 중단한 기록.

### 중단 기록의 변환 검사

- 원본: 서버의 `data/recordings/lekiwi.o23w_3w0/` 아래 `episode.s9famzmv`(21프레임), `episode.lhacty6j`(16프레임).
- 두 기록 모두 `complete=true`, `success=false`로 저장했습니다.
- 변환 결과: 서버의 `data/datasets/tailscale-recovery-check-20260913`.
- LeRobot v3.0, 2에피소드·37프레임·30fps, 상태/행동 각각 9개 값을 확인했습니다.
- 모든 원본 프레임·이미지 해시·시각 연결과, 에피소드별 처음/중간/마지막 상태·행동 및 두 영상 디코딩 검사를 통과했습니다.
- 해당 데이터셋의 `recording_report.json`에 검증 결과가 있습니다.
- 이 두 에피소드는 고정된 시험 입력으로 녹화 복구를 검사한 자료입니다. 실제 리더 시연 데이터와 구분하며, 작업 설명에도 `synthetic input`을 표시했습니다. Hugging Face에는 업로드하지 않았습니다.

이 결과는 한 쌍의 장비에서 수행한 복구 검사입니다. 15쌍 동시 사용, 장시간 수업 안정성,
ACT 학습 시작·추론을 포함한 최종 리허설은 별도 확인 항목입니다.

## 최종 적용 상태

- 핫스팟 실기를 마친 뒤 서버를 회사 Wi-Fi로 전환했습니다. LAN 주소는 `192.168.0.171`, Tailscale 주소는 `100.66.115.54`로 접속했습니다.
- 서버의 기존 수정 파일은 보존하고, 현재 프로젝트의 필요한 파일만 별도 빌드 입력으로 전달해 이미지를 다시 만들었습니다.
- 서버 `lekiwi-sim:0.1.0`: `sha256:3cf5e6fc12f422abae0d2448872c1818ad99f24e0a404837cc1949f90d3d5b9b`.
- 리더 `lekiwi-leader:0.1.0`: `sha256:30926008b06c18fa1bd1dfd5e5c6b1ba1b561a87b8783a9820116c4d12764178`.
- 서버 빌드의 자산 검사를 통과했습니다. 새 `session._jx6exrd`에서 `LEKIWI_DRIVE result=READY`와 1280×720 영상 수신을 확인했습니다.
- 실행 컨테이너의 런타임 5개 파일과 0·4·6장 README·Notion ZIP 6개 파일의 SHA-256이 현재 프로젝트와 일치했습니다.
- 최종 화면 확인은 회사망에서 진행했으며, 앞 절의 핫스팟 실기와 구분합니다. 실제 리더 입력 프로그램은 종료한 상태입니다.
