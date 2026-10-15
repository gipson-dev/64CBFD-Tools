"""Exact-input successor for the updater's source, guard append and linked image."""
import hashlib
from pathlib import Path

from tools.experiments import game_packed_record_updater as source

AFTER = {
    'elf': '42f179ad6efccc701900d9345de5a57c80aab7254e0c48d06c98d0f47e1f5422',
    'preset_owner': 'ebbba82f26704db4a11c78c43986dfd535f242c96965a2e637568fa33b814275',
    'guards': '148fb6500b75e725b6b98fe056c45b72d111eab0c93567e1beb397e9fd2741a4',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    payload = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(payload).hexdigest() == expected, 'Modified packed-updater fixture: ' + key
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
        assert hashlib.sha256(payload).hexdigest() == AFTER[key], 'Unexpected packed-updater input: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(payload)
        assert fixture(root, 'after', key) == payload
