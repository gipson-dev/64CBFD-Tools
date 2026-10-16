"""Immutable predecessor and predicted installed scaled-spray successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_scaled_random_spray as source

AFTER = {
    'elf': '2721ebd301a677eedb468dbebcd2cef9d685dfd313aded8c4785177d8a54afb4',
    'preset_owner': '5d185b496b158910ff0a7b1f1fc69077602d2abb9f9bb2db4126b77c443456c6',
    'guards': 'dc3969cde15479bc33254ab470242a65a80496e14fee28d7512ec2bb54d40399',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == expected, 'Modified spray fixture: ' + key
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
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected spray successor: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root, 'after', key) == data
