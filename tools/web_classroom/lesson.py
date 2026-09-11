#!/usr/bin/env python3
"""브라우저 터미널에서 서버의 교육 실습만 실행합니다. Docker 권한은 사용하지 않습니다."""
import argparse
import getpass
import json
import os
import socket
import sys

MAX_REQUEST = 8192


def request(message, path=None):
    payload = json.dumps(message, ensure_ascii=False).encode() + b"\n"
    if len(payload) > MAX_REQUEST:
        raise ValueError("요청이 너무 큽니다.")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(65)
        client.connect(path or os.environ.get("LEKIWI_CONTROL_SOCKET", "/run/lekiwi/control.sock"))
        client.sendall(payload)
        with client.makefile("rb") as response:
            raw = response.readline(100_000)
    result = json.loads(raw)
    if not result.get("ok"):
        raise RuntimeError(result.get("error", "실습 실행기에 연결하지 못했습니다."))
    return result["result"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="op", required=True)
    run = commands.add_parser("run", help="예: lesson run 1 / lesson run --file 학생파일.py")
    run.add_argument("chapter", nargs="?", type=int, choices=range(1, 7))
    selection = run.add_mutually_exclusive_group()
    selection.add_argument("--file", dest="script")
    selection.add_argument("--experiment", type=int, choices=range(1, 7))
    run.add_argument("--teleop", action="store_true", help="6장: 노트북의 리더 입력 수신")
    for name, help_text in (("stop", "저장 후 현재 실습 종료"), ("status", "준비·실행 상태 확인"),
                            ("logs", "현재 실습의 최근 로그 확인")):
        commands.add_parser(name, help=help_text)
    args = parser.parse_args(argv)
    message = vars(args)
    if args.op == "run":
        if args.chapter and (args.script or args.experiment):
            parser.error("장 번호와 --file/--experiment는 함께 지정하지 않습니다.")
        if not (args.chapter or args.script or args.experiment):
            parser.error("장 번호 또는 --file/--experiment를 지정하세요.")
        if args.script:
            message["script"] = os.path.abspath(args.script)
        if args.teleop:
            if args.chapter != 6 or args.script or args.experiment:
                parser.error("리더 입력은 lesson run 6 --teleop으로 시작하세요.")
            if not sys.stdin.isatty():
                raise RuntimeError("리더 접속 문구는 브라우저 터미널에서 숨김 입력하세요.")
            message["phrase"] = getpass.getpass("노트북에서도 사용할 접속 문구(12자 이상): ")
            if len(message["phrase"]) < 12:
                raise ValueError("접속 문구는 12자 이상입니다.")
    result = request(message)
    if args.op == "logs":
        print(result["log"])
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.op == "run":
            print("lesson status로 READY를 확인한 뒤 WebRTC에서 서버 IP로 연결하세요.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"중단: {exc}", file=sys.stderr)
        sys.exit(1)
