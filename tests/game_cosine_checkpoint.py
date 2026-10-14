"""Pinned inverse of cosine's direct slot, extent and closed symbol ordering."""
import hashlib
from pathlib import Path

from tools.experiments import game_cosine_candidates as source
from tools.tests import view_fov_transfer_checkpoint

AFTER = {
    'elf': 'b87dd5bcf0d6549080560feb1122f90d7b57614bdd220c29eaa75e2d0fc0cf0b',
    'cosf': '8947b41f56a8854981be155231dfbb5d4f0b885c4c60d4cdc7bba069f8841b09',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == expected, 'Modified Game cosine fixture: ' + key
    return data


def previous_input(current, path, root):
    current = view_fov_transfer_checkpoint.previous_input(current, path, root)
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
        data = view_fov_transfer_checkpoint.previous_input((root / path).read_bytes(), path, root)
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected installed Game cosine input: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root, 'after', key) == data
