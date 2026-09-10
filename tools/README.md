# 도구 폴더

| 경로 | 실행 위치 | 역할 |
|---|---|---|
| `host_setup/` | Ubuntu 호스트 | `./lekiwi install`의 학생 PC 검사·설치. 표준 Python만 사용 |
| `classroom/` | Ubuntu 호스트 | 1~6편 로컬 창 실행·교재 열기·실행 상태·자신의 실습 종료. Python Tk 사용 |
| `check_runtime.py` | LeRobot 컨테이너 | 의존성과 CUDA 연산 검사 |
| `so101_leader.py` | 리더 컨테이너 | 사용자 확인 후 리더 보정·토크 OFF·관절 읽기 |
| `export_dataset.py` | LeRobot 컨테이너 | 저장된 에피소드를 로컬 데이터셋으로 변환 |
| `dataset_manager/` | LeRobot 컨테이너 | 공통 CLI·로컬 브라우저 화면, 로컬 시연 선택·변환·상태와 영상 검사 |

호스트 설치 도구는 Docker 이미지에 복사하지 않습니다. Docker 설치 전에도 실행해야 하기 때문입니다.
시뮬레이션 검사 코드는 `isaac_sim/`, 공통 자동 테스트는 `tests/`, 교재와 교재 전용 코드는 `isaacsim_basic/`에 둡니다.
실행 결과는 공통 `data/` 아래에 저장하며 설치 진단은 `data/setup/`을 사용합니다.
사용법은 [학생 PC 설치 안내](../docs/student-setup.md)를 참고하세요.
수집 이후에는 [데이터셋 관리 안내](../docs/dataset-manager.md)를 사용합니다.
