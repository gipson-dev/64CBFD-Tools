"""Exact-input successor for the factory's source, guards and linked image."""
import hashlib
from pathlib import Path

from tools.experiments import game_record_factory as source

AFTER = {
    'elf': 'dffd6489132224328ba1b709b24cb87d7b07556d81d8ccdc4f48cb72169ae82c',
    'preset_owner': '647b591a5a4afd82be8b37884fcdfd07df1987312c9580d232d95aafc2d65a08',
    'guards': '5d5daf3748fdb04f64d3bc337f875552b6f6e6a3dd870b74095f01d0d232eb73',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    payload = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(payload).hexdigest() == expected, 'Modified record-factory fixture: ' + key
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
        assert hashlib.sha256(payload).hexdigest() == AFTER[key], 'Unexpected record-factory input: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(payload)
        assert fixture(root, 'after', key) == payload
