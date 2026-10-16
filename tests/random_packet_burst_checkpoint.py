"""Strict direct-burst successor for subsequent same-owner recoveries."""
import hashlib
from pathlib import Path

from tools.experiments import game_random_packet_burst as source

AFTER = {
    'elf': '0f335a16152a5bed2e84ed2061e240b0bbd063130b761f6228bb42e7ebe7609e',
    'edge_wrapper_owner': '6647ef44eeb6ffda08b8fa5779240eef4d17686647502a93fe897da263a48533',
}
PATHS = {source.PATHS[k]: k for k in AFTER}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == expected, 'Changed random-burst fixture: ' + key
    return data


def previous_input(current, path, root):
    relative = Path(path).as_posix()
    prefix = Path(root).as_posix() + '/'
    if relative.startswith(prefix):
        relative = relative[len(prefix):]
    key = PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest() == AFTER[key]:
        return fixture(root, 'before', key)
    return current


def freeze_after(root):
    for path, key in PATHS.items():
        data = (root / path).read_bytes()
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected random-burst successor: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root, 'after', key) == data
