# 5편 실습 기록지

- 날짜 / 이름 / PC:
- Isaac Sim 버전:
- 저장한 에피소드 경로:

| 확인 항목 | 결과 |
|---|---|
| READY → RECORDING → UNSAVED → SAVED | |
| 프레임 수 / FPS / 총 구간 길이 | |
| 첫 current_time / 첫 episode_time | |
| 마지막 episode_time / 마지막 next_time | |
| 재생 완료 상태 / 최대 오차(rad) | |
| Discard 후 이전 저장 파일 보존 여부 | |
| 두 번째 저장 폴더가 다른지 | |
| test-recording 결과 | |

## 프레임 한 개 읽기

- frame_index:
- observation 실제각(rad):
- action 목표각(rad):
- next_observation 실제각(rad):
- 이 action이 적용되는 시간 구간:
- 다음 프레임 observation과 결과가 연결되는가?

## 생각해 볼 질문

1. UNSAVED 상태에서 창을 닫으면 어떻게 되는가?
2. 실제 시간으로 6초가 걸려도 기록 구간이 3초일 수 있는 이유는?
3. 마지막 episode_time이 약 2.9833초인데 구간 길이는 왜 3초인가?
4. 목표각을 실제 관절 관측으로 저장하면 무엇을 놓치는가?
5. 재생에서 관절 위치를 강제로 대입하는 것과 명령을 다시 적용하는 것은 어떻게 다른가?
6. 이 JSON으로 바로 ACT 집기 학습을 시작할 수 없는 이유는?
7. 실물 리더와 두 카메라로 확장할 때 시간·단위·에피소드 경계를 어떻게 정할 것인가?
