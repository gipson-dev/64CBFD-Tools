"""Exact-input inverse for original rotation assembly and truthful classification."""
import hashlib
from pathlib import Path

from tools.experiments import game_rotation_matrix_leaf as source

AFTER = {
    'elf': 'b6d087530249e76ea8bd684c32f8b5ebf0dfc7c631283931ae1611d3b5fd372a',
    'angles_owner': '6cf42acdb32617b934d526cabc47e3e5e58eb3352b5175dd19ff4b6c4ffa071d',
    'progress': '595443d0129e7d6ccd1f824b050854d5759c0f45c1af5b0818ef7cde682528ee',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    payload = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(payload).hexdigest() == expected, 'Modified rotation-leaf fixture: ' + key
    return payload


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
        payload = (root / path).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == AFTER[key], 'Unexpected rotation-leaf input: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(payload)
        assert fixture(root, 'after', key) == payload
