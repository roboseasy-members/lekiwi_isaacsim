"""Docker 실습 파일을 원래 인자로 실행하면서 공통 Isaac Sim 시작 설정을 적용합니다."""
from pathlib import Path
import runpy
import sys

from app_runtime import install_profiler_defaults


def main():
    if len(sys.argv) < 2:
        raise SystemExit("실행할 Python 파일을 지정하세요.")
    script = Path(sys.argv[1]).resolve(strict=True)
    sys.argv = [str(script), *sys.argv[2:]]
    # 원래 스크립트의 인접 모듈과 공통 런타임 모듈을 모두 찾을 수 있게 합니다.
    sys.path.insert(0, str(script.parent))
    install_profiler_defaults()
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    main()
