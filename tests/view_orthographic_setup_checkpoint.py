"""Exact-input inverse of the directly matched orthographic setup installation."""
import hashlib
from pathlib import Path

from tools.experiments import game_view_orthographic_setup as source

AFTER = {
    'elf': 'ebe9dc507cf591cb19aa4f01f20653b6c8df2bf7cba3325302738e147bd072ef',
    'owner': '4d528f1ca9f8678fd43bc2bdfb2d0ebbd155377d3a78de2d6e0f49d0b76d967c',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    digest = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == digest, 'Modified orthographic setup fixture: ' + key
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
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected installed orthographic setup input: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root, 'after', key) == data
