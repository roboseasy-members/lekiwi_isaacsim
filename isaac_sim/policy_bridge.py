"""동일 서버의 두 컨테이너 사이 ACT 입력 전달. Unix 소켓·JSON·원시 RGB만 사용합니다."""
import json
import math
import socket
import struct

import numpy as np

CAMERAS = ('front', 'wrist')
MAX_HEADER = 8192
MAX_PIXELS = 4096 * 4096


def vector(values):
    array = np.asarray(values, dtype=np.float32)
    if array.shape != (9,) or not np.isfinite(array).all():
        raise ValueError('상태·행동은 유한한 9개 값이어야 합니다.')
    return array


def receive_exact(connection, size):
    result = bytearray()
    while len(result) < size:
        part = connection.recv(min(size - len(result), 1024 * 1024))
        if not part:
            raise ConnectionError('ACT 연결이 끊겼습니다.')
        result.extend(part)
    return bytes(result)


def send_json(connection, value):
    payload = json.dumps(value, allow_nan=False).encode()
    if len(payload) > MAX_HEADER:
        raise ValueError('ACT 메시지가 너무 큽니다.')
    connection.sendall(struct.pack('!I', len(payload)) + payload)


def receive_json(connection):
    size, = struct.unpack('!I', receive_exact(connection, 4))
    if not 0 < size <= MAX_HEADER:
        raise ValueError('ACT 메시지 크기가 올바르지 않습니다.')
    result = json.loads(receive_exact(connection, size))
    if not isinstance(result, dict):
        raise ValueError('ACT 메시지는 JSON 객체여야 합니다.')
    return result


def receive_observation(connection, shapes):
    header = receive_json(connection)
    if set(header) != {'sequence', 'simulation_time', 'state', 'reset', 'shapes'}:
        raise ValueError('지원하지 않는 ACT 관측 메시지입니다.')
    if type(header['sequence']) is not int or header['sequence'] < 0 or type(header['reset']) is not bool:
        raise ValueError('ACT 관측 순서가 올바르지 않습니다.')
    stamp = header['simulation_time']
    if type(stamp) not in (int, float) or not math.isfinite(stamp) or stamp < 0:
        raise ValueError('ACT 관측 시각이 올바르지 않습니다.')
    if header['shapes'] != {key: list(value) for key, value in shapes.items()}:
        raise ValueError('학습 때와 카메라 해상도가 다릅니다.')
    state = vector(header['state'])
    images = {}
    for name in CAMERAS:
        height, width, channels = shapes[name]
        if channels != 3 or not 0 < height * width <= MAX_PIXELS:
            raise ValueError('지원하지 않는 RGB 크기입니다.')
        images[name] = np.frombuffer(receive_exact(connection, height * width * 3), dtype=np.uint8).reshape(
            height, width, 3).copy()
    return header, state, images


def query(path, sequence, simulation_time, state, images, reset, timeout=5.0):
    arrays = {name: np.asarray(images[name]) for name in CAMERAS}
    for image in arrays.values():
        if image.dtype != np.uint8 or image.ndim != 3 or image.shape[-1] != 3 or image.size > MAX_PIXELS * 3:
            raise ValueError('ACT 입력은 RGB uint8 영상이어야 합니다.')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(timeout)
        connection.connect(str(path))
        send_json(connection, {'sequence': sequence, 'simulation_time': simulation_time,
                              'state': vector(state).tolist(), 'reset': reset,
                              'shapes': {key: list(value.shape) for key, value in arrays.items()}})
        for name in CAMERAS:
            connection.sendall(arrays[name].tobytes())
        result = receive_json(connection)
    if result.get('sequence') != sequence or result.get('simulation_time') != simulation_time:
        raise ValueError('다른 시점의 ACT 응답은 적용하지 않습니다.')
    if 'error' in result:
        raise RuntimeError(result['error'])
    return vector(result['action'])
