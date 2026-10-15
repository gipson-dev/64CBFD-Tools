"""Exact-hash inverse of the FOV transfer slot, extent, source and guards."""
import hashlib
from pathlib import Path

from tools.experiments import game_view_fov_transfer_candidates as source
from tools.tests import view_projection_family_checkpoint as family_checkpoint

AFTER = {
    'elf': 'f36703ce83adebb99de90c1bc8061eec68431f36f6a366b90b2a331d25574c1a',
    'owner': '831ac69eb405bc46db96cf7f76d032f9eb9b021c89192f60843b2cd6e615f2d8',
    'guards': 'c0bf9a67de2d35e5acb65eb383e82d9b6cd78323866ed44cba6a26c5998baf94',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    digest = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == digest, 'Modified view transfer fixture: ' + key
    return data


def previous_input(current, path, root):
    current = family_checkpoint.previous_input(current, path, root)
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
        data = family_checkpoint.previous_input((root / path).read_bytes(), path, root)
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected installed view transfer input: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root, 'after', key) == data
