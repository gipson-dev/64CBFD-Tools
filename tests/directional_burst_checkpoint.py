"""Directional-burst successor predicted before source and guard installation."""
import hashlib
from pathlib import Path

from tools.experiments import game_directional_burst_match as source

AFTER = {
    'elf': '1231fc461203e639a7667bead7e0313e477ef41f98b8bab926f8a29bb0ef2baa',
    'preset_owner': '4220487d888963d7180094236bcf985e1fbcf61541b50064ab710b974c5e026c',
    'guards': '0395585b3026b6dabd2df7c306b80a8c7c0450fa57b99767fa08319e9be7737b',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    payload = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(payload).hexdigest() == expected, 'Modified directional-burst fixture: ' + key
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
        assert hashlib.sha256(payload).hexdigest() == AFTER[key], 'Unexpected directional-burst successor: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(payload)
        assert fixture(root, 'after', key) == payload
