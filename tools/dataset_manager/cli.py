"""Local dataset CLI, shared with the classroom browser UI."""
import argparse
from contextlib import nullcontext
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core


def parser():
    p = argparse.ArgumentParser(description='LeKiwi 로컬 데이터셋 관리')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('list')
    convert = sub.add_parser('export')
    convert.add_argument('--episode', action='append', required=True)
    convert.add_argument('--name', required=True)
    convert.add_argument('--success-only', action='store_true')
    inspect = sub.add_parser('inspect')
    inspect.add_argument('--name', required=True)
    upload = sub.add_parser('upload')
    upload.add_argument('--name', required=True)
    upload.add_argument('--repo-id', required=True)
    visibility = upload.add_mutually_exclusive_group(required=True)
    visibility.add_argument('--private', action='store_true')
    visibility.add_argument('--public', action='store_true')
    sub.add_parser('serve')
    check = sub.add_parser('_validate')
    check.add_argument('path')
    return p


def main():
    args = parser().parse_args()
    if args.command == 'serve':
        from server import serve
        serve()
        return
    try:
        with core.operation_lock() if args.command != '_validate' else nullcontext():
            if args.command == 'list':
                result = core.inventory()
            elif args.command == 'export':
                result = core.export_selected(args.episode, args.name, args.success_only)
            elif args.command == 'inspect':
                result = core.inspect_dataset(args.name)
            elif args.command == 'upload':
                stream = getattr(sys.stdin, 'buffer', sys.stdin)
                raw = stream.readline(1025)
                if isinstance(raw, bytes):
                    raw = raw.decode('utf-8', errors='strict')
                token = raw.rstrip('\r\n')
                if len(raw) > 1024 or '\n' in token or '\r' in token:
                    raise core.UserError('Hugging Face 토큰 입력이 올바르지 않습니다.')
                result = core.upload_dataset(args.name, args.repo_id, args.private, token)
                token = ''
            else:
                result = core._validate_dataset(Path(args.path))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(core.safe_error(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
