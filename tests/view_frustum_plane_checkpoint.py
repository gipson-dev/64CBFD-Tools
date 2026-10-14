"""Pinned inverse of the view-plane slot, extent, owner and four guards."""
import hashlib
from pathlib import Path

from tools.experiments import game_view_frustum_plane_candidates as source

AFTER = {
    'elf': '79eb4f3261dcc2cff366d6e1dcddef48cb1c6e6b923821272d3b56c709a82e10',
    'owner': '8bba4f1abbd69d9032a5fe0be73238d84f6b13ecf44716938037ef03f9cb0aae',
    'guards': 'b0f5425a5a3fbe2a1a44898f5c5499b781cf0598532b595dae1c81c7534b4d99',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    digest = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == digest, 'Modified view-plane fixture: ' + key
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
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected installed view-plane input: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root, 'after', key) == data
