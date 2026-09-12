#!/usr/bin/env python3
"""브라우저 터미널에서 서버의 교육 실습과 로컬 데이터셋 작업을 실행합니다."""
import argparse
import getpass
import json
import os
import socket
import sys
import time

MAX_REQUEST = 8192
MAX_RESPONSE = 8_000_000


def request(message, path=None):
    payload = json.dumps(message, ensure_ascii=False).encode() + b"\n"
    if len(payload) > MAX_REQUEST:
        raise ValueError("요청이 너무 큽니다.")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(65)
        client.connect(path or os.environ.get("LEKIWI_CONTROL_SOCKET", "/run/lekiwi/control.sock"))
        client.sendall(payload)
        with client.makefile("rb") as response:
            raw = response.readline(MAX_RESPONSE + 1)
            if len(raw) > MAX_RESPONSE or not raw.endswith(b"\n"):
                raise RuntimeError("실행기의 응답이 너무 크거나 연결이 끊겼습니다. 상태를 다시 확인하세요.")
    result = json.loads(raw)
    if not result.get("ok"):
        raise RuntimeError(result.get("error", "실습 실행기에 연결하지 못했습니다."))
    return result["result"]


def dataset(message):
    result = request(message)
    if message['action'] == 'logs':
        print(result['log'])
        return
    if message['action'] in ('status',):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    identity = result['job_id']
    print(f"데이터셋 작업 시작: {identity}", flush=True)
    try:
        while result['state'] == 'RUNNING':
            print(f"진행 중 · {result['elapsed_seconds']:.1f}초 경과 · lesson dataset logs로 상세 확인", flush=True)
            time.sleep(2)
            result = request({'op': 'dataset', 'action': 'status', 'job_id': identity})
    except KeyboardInterrupt:
        print(f"\n화면 대기를 끝냈습니다. 서버 작업은 계속됩니다. lesson dataset status --job-id {identity}")
        return
    except (OSError, RuntimeError):
        print(f"연결을 다시 확인한 뒤 lesson dataset status --job-id {identity}로 작업 상태를 확인하세요.", file=sys.stderr)
        raise
    if result['state'] != 'SUCCEEDED':
        raise RuntimeError(result.get('error', '데이터셋 작업 실패'))
    print(json.dumps(result['result'], ensure_ascii=False, indent=2))
    print('LEKIWI_DATASET_JOB result=PASS', flush=True)


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
    data = commands.add_parser('dataset', help='저장한 시연 목록·LeRobot 변환·검사·선택 업로드')
    operations = data.add_subparsers(dest='action', required=True)
    operations.add_parser('list', help='완료된 시연과 변환된 데이터셋 목록')
    export = operations.add_parser('export', help='선택한 시연을 새 데이터셋으로 변환')
    export.add_argument('--episode', dest='episodes', action='append', required=True)
    export.add_argument('--name', required=True)
    export.add_argument('--success-only', action='store_true')
    inspect = operations.add_parser('inspect', help='데이터·영상 재열기 검사')
    inspect.add_argument('--name', required=True)
    upload = operations.add_parser('upload', help='검사를 통과한 데이터셋을 Hugging Face에 업로드')
    upload.add_argument('--name', required=True)
    upload.add_argument('--repo-id', required=True)
    visibility = upload.add_mutually_exclusive_group(required=True)
    visibility.add_argument('--private', action='store_true')
    visibility.add_argument('--public', dest='private', action='store_false')
    for action in ('status', 'logs'):
        operations.add_parser(action).add_argument('--job-id')
    args = parser.parse_args(argv)
    message = vars(args)
    if args.op == 'dataset':
        if args.action == 'upload':
            if not sys.stdin.isatty():
                raise RuntimeError('Hugging Face 토큰은 브라우저 터미널에서 숨김 입력하세요.')
            token = getpass.getpass('Hugging Face 쓰기 토큰(저장하지 않음): ')
            message['token'] = token
            try:
                dataset(message)
            finally:
                message.pop('token', None)
                token = None
        else:
            dataset(message)
        return
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
