"""Quad-emitter prediction plus its separately qualified symbol serialization."""
import hashlib
from pathlib import Path

from tools.experiments import game_quad_edge_match as source

AFTER = {
    'elf': 'dc87be7c3563be172635567a5ab5ad2e1d3e1c102ae9c93763b115c0d716428a',
    'preset_owner': 'a1bfba9c79944684bb9dfe21bdeed3a01dccc98e8b635c74b36fb5930e20b5db',
    'guards': '6e6a9828f203dee57f7156cfec58721eeabd23c3bdb7301b4d51cb0f1fc757fa',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == expected, 'Modified quad-emitter fixture: ' + key
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
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected quad-emitter successor: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root, 'after', key) == data
