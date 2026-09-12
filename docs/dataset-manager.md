# 로컬 데이터셋 관리와 학습 준비

교육 흐름은 **환경 준비 → 1~6편 교육·teleop → 로컬 수집·변환 → 로컬 학습 → Isaac Sim 추론**입니다.
6편에서 저장한 시연을 선택하고 LeRobot 데이터셋으로 변환·검사합니다.
변환·학습은 로컬만으로 진행할 수 있습니다. 필요한 학생은 검사 완료 후 별도 스크립트로 Hugging Face에 선택 업로드할 수 있습니다.

[브라우저 VS Code 수업](browser-classroom.md#7-python-파일을-수정하고-데이터-변환검사)에서는
6장의 `02_dataset_list.py` → `03_convert_dataset.py` → `04_inspect_dataset.py`를 실행합니다.
선택 업로드는 마지막에 `05_upload_dataset.py`를 실행합니다.
필요한 에피소드·이름·성공 여부 조건은 파일 상단에서 수정하고, 터미널에서는 `python3 파일명.py`만 실행합니다.
아래 `./lekiwi` 명령은 서버 호스트 터미널용입니다.

## 실행

코드를 업데이트한 뒤 이미지를 다시 빌드합니다.
Docker에 sudo가 필요한 PC에서는 먼저 `export LEKIWI_DOCKER_SUDO=1`을 실행하세요.

```bash
./lekiwi setup lerobot
./lekiwi dataset-ui
```

터미널에 표시된 `http://127.0.0.1:8765/#...` 전체 주소를 같은 PC의 브라우저에서 엽니다.
`#` 뒤 값은 이번 로컬 관리 화면에 접속하는 임시 키입니다. 별도의 계정이나 토큰 입력은 필요 없습니다.
한 PC에서는 관리 화면 하나만 실행합니다. 작업 완료 후 실행 터미널에서 Ctrl+C로 종료합니다.
실행기는 자신이 만든 관리 컨테이너만 종료합니다. Isaac Sim을 종료해도 이 관리 화면은 유지됩니다.

## 화면에서 진행하기

1. **완료된 시연 선택:** F7/F9 저장이 완료된 시연을 선택합니다.
   작업·프레임 수·성공 표시와 첫 전방·손목 영상을 확인합니다.
   첫 프레임 미리보기는 전체 시연의 품질이나 집기 성공 검증을 대신하지 않습니다.
2. **로컬 데이터셋으로 변환:** 새 데이터셋 이름을 입력합니다.
   여러 수집 세션의 에피소드를 함께 선택할 수 있지만 카메라 설정이 같아야 합니다.
   ‘성공으로 표시한 시연만 포함’을 선택하면 성공 미표시 시연은 제외합니다.
3. **학습 전 데이터 확인:** 변환된 데이터셋을 선택하고 상태·영상 검사를 실행합니다.
   프레임·에피소드 수, 상태·행동의 순서와 카메라 규격을 확인하고,
   처음·중간·마지막의 상태·행동과 두 영상을 읽어 검사합니다.
   결과에 표시된 로컬 경로를 학습 입력으로 사용합니다.

이 도구는 이 프로젝트에서 만든 **LeKiwi 30 Hz·전방/손목 RGB·9개 상태/행동 데이터셋**을 대상으로 합니다.
변환·검사 중에는 진행 상태가 표시되며 중복 작업을 막습니다. 중도 취소·재개 UI는 아직 없습니다.

## CLI로 같은 작업 실행

```bash
./lekiwi dataset list
./lekiwi dataset export \
  --episode lekiwi.SESSION/episode.EPISODE \
  --name basket_01
./lekiwi dataset inspect --name basket_01
```

`SESSION`과 `EPISODE`는 목록에서 확인한 실제 값으로 바꾸세요.
`--episode`는 여러 번 지정할 수 있고 `--success-only`로 성공 표시 시연만 포함할 수 있습니다.
데이터셋 이름은 영문·숫자로 시작하고 영문·숫자·점·밑줄·하이픈만 사용합니다.
내부 식별자는 `local/basket_01`처럼 자동 생성됩니다. 이것은 LeRobot 파일 형식에 필요한 값이며 온라인 저장소를 만들지 않습니다.
기존 `./lekiwi export-dataset` 명령도 유지합니다.

## 파일과 실패 처리

- 원본: 컨테이너 `/data/recordings`, 기본 호스트 `data/recordings`.
- 변환 결과: 컨테이너 `/data/datasets/새이름`, 기본 호스트 `data/datasets/새이름`.
- 검사·출처 정보: 각 데이터셋의 `recording_report.json`.
- 원본은 보존하고 새 폴더에 변환합니다. `.partial` 기록은 목록에서 제외합니다.
- 기존 출력은 덮어쓰지 않습니다. 실패한 변환 출력은 보존하며 새 이름으로 재시도합니다.
- 관리 CLI·화면은 오프라인 모드로 실행합니다. 설치된 이미지로 시연 조회·변환·검사를 하는 데 인터넷이 필요하지 않습니다.
- 데이터와 캐시는 Git 및 Docker 이미지에 포함되지 않으며 컨테이너 종료 후에도 유지됩니다.

## 선택: Hugging Face에 업로드

업로드하지 않아도 로컬 학습을 진행할 수 있습니다. 업로드하려면 브라우저 VS Code에서
`06_lekiwi_dataset/experiments/05_upload_dataset.py`를 열고 상단의 `dataset_name`, `repo_id`, `private`를 수정합니다.
기본값은 `private = False`로 공개 업로드합니다. 비공개가 필요하면 `True`로 바꿉니다.
저장한 뒤 같은 폴더의 터미널에서 실행합니다.

```bash
python3 05_upload_dataset.py
```

터미널이 Hugging Face **쓰기 권한 토큰**을 물으면 붙여 넣고 Enter를 누릅니다. 입력 문자는 화면에 표시되지 않습니다.
토큰은 [Hugging Face Access Tokens 설정](https://huggingface.co/settings/tokens)에서 본인 계정의 쓰기 권한으로 발급합니다.
토큰은 Python 파일, 명령행, 작업 로그, 로그인 캐시에 저장하지 않고 익명 파이프로 서버 컨테이너에 한 번 전달합니다.
로컬 데이터셋 검사를 먼저 통과한 뒤 `data/`, `meta/`, `videos/`와 자동 생성한 `README.md` 카드를 업로드합니다.
로컬 원본 경로와 카메라 검사 기록이 담긴 `recording_report.json`은 업로드하지 않습니다.
카드에는 에피소드·프레임 수, 영상·상태·행동 규격, 성공 표시 집계와 Visualize Dataset 링크가 들어갑니다.
[LeRobot 공식 카드 구성](https://github.com/huggingface/lerobot/blob/v0.6.1/src/lerobot/datasets/utils.py#L393)에 맞춰
`LeRobot`·`robotics` 메타데이터와 `data/*/*.parquet`만 읽는 표 보기 설정도 추가합니다.
데이터셋 라이선스는 임의로 지정하지 않습니다.

새 저장소 이름을 사용합니다. 기존 저장소의 공개 범위가 `private` 설정과 다르거나 데이터·`v3.0` 태그가
이미 있으면 중단합니다. README·Git 설정 파일만 있는 빈 저장소는 사용할 수 있습니다.
업로드한 파일 목록에 모든 학습 파일과 카드가 있는지 확인하고, 카드까지 포함한 업로드에 `v3.0` 태그를 붙여 다시 확인합니다.
이 태그는 [LeRobot 0.6.1의 기본 Hub 로더](https://github.com/huggingface/lerobot/blob/v0.6.1/src/lerobot/datasets/utils.py#L326)가 데이터를 찾을 때 사용합니다.
성공하면 저장소 주소, `revision: v3.0`, `LEKIWI_DATASET_JOB result=PASS`가 출력됩니다.
업로드 중단 후 원격 파일이 남았다면 새 저장소 이름으로 재시도합니다. 기존 원격 파일·태그는 자동 삭제하지 않습니다.
업로드에만 인터넷이 필요하며 목록·변환·검사는 계속 오프라인으로 실행됩니다.

## 로컬 학습과 추론으로 이어가기

기존 학습 CLI에 로컬 데이터 경로를 지정합니다. 다음은 실행 형태 예시이며,
우리 로봇에 맞춘 학습 설정과 학습→모델 재로딩→추론의 전체 검증은 아직 남아 있습니다.

```bash
./lekiwi train act \
  --dataset.repo_id=local/basket_01 \
  --dataset.root=/data/datasets/basket_01 \
  --output_dir=/data/outputs/act_basket_01 \
  --batch_size=4 --steps=1000
```

학습 출력은 `data/outputs`에 보관하고 이후 Isaac Sim에서 모델을 불러와 평가하는 흐름입니다.
기존 데이터셋을 사용한다면 `recording_report.json`의 식별자를 `--dataset.repo_id`에 지정합니다.
학습·추론 화면은 아직 준비 중입니다. 선택한 모델의 사전학습 가중치는 최초 다운로드가 필요할 수 있으므로,
데이터셋을 로컬에서 사용하는 것과 전체 학습 과정이 완전히 오프라인인 것은 구분합니다.

## 검증 범위

실제 데이터셋의 오프라인 재열기와 상태·영상 검사, 브라우저의 시연 선택·미리보기·변환을 검증합니다.
단위 테스트는 원본 보존·미완성/중복 출력 거부·원본 경로 보존·외부 요청/중복 작업 차단을 포함합니다.
학습 성능이나 집기 성공률은 이 검사로 보장하지 않습니다.
