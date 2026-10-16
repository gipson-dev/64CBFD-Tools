"""Immutable debris predecessor and fully accounted serialization successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_six_piece_debris_match as source

AFTER = {
    'elf': '9110fcc52b4a87dbbc8aed553daf25789ab8810bff2b962cadee6f001fe96283',
    'edge_wrapper_owner': '93485699f28006bd236fdde7e64a2a328b6f1b52144d86bee1742af9b4d2604f',
    'guards': 'a5f47cb991e377c7f9e80faa896b4db392a7999273a958520dcc61d9d1b22b62',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == expected, 'Modified debris-match fixture: ' + key
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
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected debris-match successor: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root, 'after', key) == data
