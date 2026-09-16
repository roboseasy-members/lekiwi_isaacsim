"""6장 · 변환된 데이터셋을 다시 열어 상태·영상이 함께 읽히는지 검사하는 코드.

실행: 저장소 최상위 폴더에서 python3 isaacsim_basic/06_lekiwi_dataset/experiments/04_inspect_dataset.py
준비: 03_convert_dataset.py의 변환이 오류 없이 완료된 데이터셋.

읽는 순서: dataset_name을 변환 때의 이름으로 설정 → main()의 dataset inspect → 결과 확인.
이 파일은 변환된 데이터를 다시 만드는 대신 기존 결과를 읽어 검사합니다.
완료 기준: 오류 없이 결과 JSON이 출력되고 데이터셋 이름·에피소드 수·프레임 수·경로를 확인합니다.
검사 통과는 학습 입력 형식 확인이며 학습 완료나 집기 성공을 뜻하지 않습니다.
다음 단계: 06_train_act.py에서 같은 dataset_name을 사용합니다. 업로드는 선택입니다.
문법 안내와 실행 흐름: isaacsim_basic/CODE_GUIDE.md"""
from pathlib import Path
import subprocess

# __file__은 이 파일의 위치입니다. 이 위치를 기준으로 저장소의 lekiwi 실행기를 찾습니다.
launcher = Path(__file__).resolve().parents[3] / "lekiwi"

# 변환할 때 사용한 dataset_name과 동일하게 적습니다.
dataset_name = 'lekiwi_lesson6_01'


def main():
    # 이 파일은 데이터를 수정하지 않고 같은 노트북에서 상태·영상 파일을 다시 읽어 검사합니다.
    """위 설정을 프로젝트 실행 명령에 전달하고 실제 작업의 성공·실패 종료 코드를 반환합니다."""
    if not isinstance(dataset_name, str):
        raise SystemExit('dataset_name은 따옴표로 감싼 데이터셋 이름으로 설정하세요.')
    # 성공하면 프레임·에피소드 수와 노트북의 학습 입력 경로가 출력됩니다.
    result = subprocess.run([str(launcher), 'dataset', 'inspect', '--name', dataset_name])
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit('작업을 중단했습니다. 터미널의 오류와 ./lekiwi status를 확인하세요.')
