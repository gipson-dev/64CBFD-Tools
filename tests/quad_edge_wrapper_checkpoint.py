"""Exact successor predicted before the rectangle-wrapper installation."""
import hashlib
from pathlib import Path

from tools.experiments import game_quad_edge_wrapper_match as source

AFTER = {
    'elf': '988b1f5cb7abe8a46f965e73661f544c756549411b92f5b6f0334e3be7504f92',
    'edge_wrapper_owner': '4a56e7b48f45efeb13d0909d18f60d0a4f51257d224828a39e729c5f0a42a44c',
    'guards': '116d6f30b154c06e916d1c868f56e5352ae619d65f7e7f8b97ecd27a97fe1044',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    payload = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(payload).hexdigest() == expected, 'Modified rectangle-wrapper fixture: ' + key
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
        assert hashlib.sha256(payload).hexdigest() == AFTER[key], 'Unexpected rectangle-wrapper input: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(payload)
        assert fixture(root, 'after', key) == payload
