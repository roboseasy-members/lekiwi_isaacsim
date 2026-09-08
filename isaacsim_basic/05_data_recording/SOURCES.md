# 5편 출처와 검증

문서 확인일: 2026-09-08. 실습 대상: Isaac Sim 5.1.0 Docker.

- [NVIDIA Data Logging 5.1](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/core_api_tutorials/tutorial_advanced_data_logging.html): DataLogger의 기록·저장·재생 흐름.
- [NVIDIA Core API 5.1 — DataLogger](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/py/source/extensions/isaacsim.core.api/docs/index.html): 기록기 메서드와 인자.
- [LeRobotDataset v3](https://huggingface.co/docs/lerobot/main/lerobot-dataset-v3): 수치·영상·메타데이터를 포함한 후속 데이터셋 구조. 이번 JSON을 그 형식으로 변환한 것은 아님.
- 이미지 내부 `isaacsim.core.api/loggers/data_logger.py`: 설치된 API를 직접 확인. `add_data()`는 시작 여부를 자체 검사하지 않으므로 호출 측에서 제어.
- [실습 코드](../recording.py), [모형 생성 코드](../scenes.py): 2편의 한 관절 모형을 재사용하고, 교재 전용 패널과 상태·행동·다음 상태 기록을 새로 구현.

## 검증 범위

- 실제 PhysX 자동 검사: 60 Hz·180프레임 수집, 파일 재읽기, 저장 명령 재생 통과.
- 제작 PC 자동 재생 최대 상태 오차: 0 rad. 허용 기준은 0.01 rad 미만이며 다른 환경에서 같은 오차를 보장하지 않음.
- 새 기록 취소 후 기존 저장 파일 보존 검사 통과.
- 빈 기록·누락 스텝·NaN·관측 짝 불일치·시간 간격 오류 거부 검사 통과.
- 실제 GUI 캡처와 문서·ZIP 검사는 전체 [검증 기록](../VALIDATION.md)에 기록.
- 실물 리더·모터, 카메라 영상 기록, LeRobot 변환, 정책 학습·집기 성공은 이번 검증 범위에 없음.

캡처는 실제 교육용 Isaac Sim 창을 사용합니다. 원본 PNG 위에 SVG 사각형과 별도 하단 설명을 합성하며,
버튼이나 측정 숫자를 생성형 이미지로 다시 만들지 않습니다.


## 준비 구간 개선 검증 · 2026-09-08

- 모형을 SingleArticulation으로 등록하고 `post_reset()`으로 기본 상태를 복원합니다. PREPARING 중 준비 물리 스텝을 나누어 실행하며 UI 갱신을 계속합니다.
- GUI에서 기록·재생 준비의 최대 갱신 간격 22.4/23.0ms, 180프레임 재생 최대 상태 오차 0rad를 확인했습니다. 저장·완료 UI 전환에는 약 0.10초 지연이 남아 있습니다.
- 기존 스크린샷은 같은 Record/Save/Replay 절차의 앞선 실행입니다. 추가된 PREPARING 상태는 본문에 설명했습니다.
