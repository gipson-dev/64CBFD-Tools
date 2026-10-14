"""Exact-hash inverse of sine's code, extent and closed symbol metadata."""
import hashlib
from pathlib import Path

from tools.experiments import game_trig_candidates as source

AFTER = {
    'elf': 'e7966de8419027fba66c6d9ae8a2853ec5b3d0ce756303a823daa4b24e8e9fe9',
    'sinf': 'ae271497692ea1a00abd96bcfed9209458cf8ea694b0df385aa5dddf9fc1a679',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    digest = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == digest, 'Modified Game sine fixture: ' + key
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
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected installed Game sine input: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root, 'after', key) == data
