"""Exact-input successor for the independently predicted table-fade match."""
import hashlib
from pathlib import Path

from tools.experiments import game_table_fade_match as source

AFTER = {
    'elf': '43f01cd6db9d414aa372134ab47ee0d464ea53cc79200be7922dd96cf3644b09',
    'preset_owner': '89f090fd6271117e29c2faa1ca5a6609ca846618931fb76e23d4b71d98cb96d9',
    'guards': '29d703d96e0013c3b74e85e4afc6923b810f3e7e2096c0b6bfe8d044ec72fdaa',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    payload = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(payload).hexdigest() == expected, 'Modified table-fade fixture: ' + key
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
        assert hashlib.sha256(payload).hexdigest() == AFTER[key], 'Unexpected table-fade input: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(payload)
        assert fixture(root, 'after', key) == payload
