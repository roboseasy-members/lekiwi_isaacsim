"""ACT 수업 실행 옵션. 호스트·브라우저 요청에 같은 검사를 적용합니다."""
import argparse
from pathlib import Path
import re


def name(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}', value):
        raise ValueError('이름은 영문·숫자로 시작하고 영문·숫자·점·밑줄·하이픈만 사용하세요.')
    return value


def contained(parent, *parts):
    parent = Path(parent).resolve()
    path = parent.joinpath(*parts).resolve()
    if not path.is_relative_to(parent) or path == parent:
        raise ValueError('지정된 데이터 폴더 밖의 경로는 사용할 수 없습니다.')
    return path


def arguments(parser, mode):
    parser.add_argument('--run-name', required=True)
    parser.add_argument('--device', choices=('cuda', 'cpu'), default='cuda')
    if mode == 'train':
        source = parser.add_mutually_exclusive_group(required=True)
        source.add_argument('--dataset-name')
        source.add_argument('--repo-id')
        parser.add_argument('--steps', type=int, default=1000)
        parser.add_argument('--batch-size', type=int, default=4)
        parser.add_argument('--num-workers', type=int, default=0)
        parser.add_argument('--pretrained-backbone', action=argparse.BooleanOptionalAction, default=True)
    else:
        parser.add_argument('--checkpoint', default='last')
        parser.add_argument('--seconds', type=int, default=30)


def validate(message, mode):
    common = {'run_name', 'device'}
    extra = ({'dataset_name', 'repo_id', 'steps', 'batch_size', 'num_workers', 'pretrained_backbone'}
             if mode == 'train' else {'checkpoint', 'seconds'})
    if set(message) - common - extra:
        raise ValueError('지원하지 않는 ACT 실행 옵션입니다.')
    result = dict(message)
    name(result.get('run_name'))
    result.setdefault('device', 'cuda')
    if result['device'] not in ('cuda', 'cpu'):
        raise ValueError('device는 cuda 또는 cpu입니다.')
    if mode == 'train':
        dataset, repo = result.get('dataset_name'), result.get('repo_id')
        if (dataset is None) == (repo is None):
            raise ValueError('로컬 dataset_name 또는 공개 repo_id 중 하나를 지정하세요.')
        if dataset is not None:
            name(dataset)
        if repo is not None and (not isinstance(repo, str) or not re.fullmatch(
                r'[A-Za-z0-9][A-Za-z0-9._-]{0,95}/[A-Za-z0-9][A-Za-z0-9._-]{0,95}', repo)):
            raise ValueError('repo_id는 계정명/데이터셋명 형식입니다.')
        for key, default, low, high in [('steps', 1000, 1, 10000000), ('batch_size', 4, 1, 256),
                                       ('num_workers', 0, 0, 32)]:
            result.setdefault(key, default)
            if type(result[key]) is not int or not low <= result[key] <= high:
                raise ValueError(f'{key}는 {low}~{high} 정수입니다.')
        result.setdefault('pretrained_backbone', True)
        if type(result['pretrained_backbone']) is not bool:
            raise ValueError('pretrained_backbone은 True 또는 False입니다.')
    else:
        result.setdefault('checkpoint', 'last')
        if not isinstance(result['checkpoint'], str) or not re.fullmatch(r'last|[0-9]{1,12}', result['checkpoint']):
            raise ValueError('checkpoint는 last 또는 저장된 단계 번호입니다.')
        result.setdefault('seconds', 30)
        if type(result['seconds']) is not int or not 1 <= result['seconds'] <= 3600:
            raise ValueError('seconds는 1~3600 정수입니다.')
    return result


def cli_args(options):
    args = []
    for key, value in options.items():
        if value is None:
            continue
        flag = '--' + key.replace('_', '-')
        if type(value) is bool:
            args.append(flag if value else '--no-' + key.replace('_', '-'))
        else:
            args += [flag, str(value)]
    return args
