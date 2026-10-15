"""Exact successor predicted before installing the direct fade/acceleration callback."""
import hashlib
from pathlib import Path

from tools.experiments import game_record_fade_acceleration as source

AFTER = {
    'elf': '7ae635c99d87e66d7d1455cb75e9ba49158107a3200511cf6a153d12e15c7d2f',
    'preset_owner': '7ee0dee3043e55bf9095c2f52c00f552bcc8ae8c02c152d5f6d5be73e8fb99a7',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    payload = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(payload).hexdigest() == expected, 'Modified fade-acceleration fixture: ' + key
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
        assert hashlib.sha256(payload).hexdigest() == AFTER[key], 'Unexpected fade-acceleration input: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(payload)
        assert fixture(root, 'after', key) == payload
