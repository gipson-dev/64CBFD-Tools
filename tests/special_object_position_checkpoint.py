"""Exact-input inverse for the attachment-position guarded installation."""
import hashlib
from pathlib import Path

from tools.experiments import game_special_object_position as source

AFTER = {
    'elf': '52b0efe2da54e3d78c4ad3ca102189d57d877ed313a245a055630650372133f6',
    'position_owner': 'c9e6044506b47ac23ef11f88612d30dd705f51cdfb287572956bea6bf24a4759',
    'guards': '311c81d50de789b4a51e3d27ac3ad2d0e0aabb9b07393ce004d34fdd1c822af2',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    payload = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(payload).hexdigest() == expected, 'Modified attachment-position fixture: ' + key
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
        assert hashlib.sha256(payload).hexdigest() == AFTER[key], 'Unexpected attachment-position input: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(payload)
        assert fixture(root, 'after', key) == payload
