"""Exact three-input successor predicted before the guarded color-fade install."""
import hashlib
from pathlib import Path

from tools.experiments import game_record_color_fade_match as source

AFTER = {
    'elf': '6ab7e9dfb4c7040b120f0a7132bf8f6fe7add5dcd0ad6b4f15732fb96eeaa1a7',
    'preset_owner': '707fe2fb844cfa755fc9d3094125781911f35d3bcf4ef60e837a0fc4522aae7f',
    'guards': '33ed02ef28b1ea65fb27f6040d7487cea86623980e41bfe2fc396cc6d92f81d5',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    payload = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(payload).hexdigest() == expected, 'Modified color-fade-match fixture: ' + key
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
        assert hashlib.sha256(payload).hexdigest() == AFTER[key], 'Unexpected color-fade-match input: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(payload)
        assert fixture(root, 'after', key) == payload
