"""Pinned source/guard/language inverse; the full linked ELF is unchanged."""
import hashlib
import json
from pathlib import Path

from tools.experiments import game_commented_notification_candidates as source
from tools.tests import codec_refill_checkpoint

AFTER = {
    'owner': '8ab68786c757c4ebcaa85e806adc337649aa67aefc4a7a2d64d7bd67bf1da846',
    'progress': 'b7d6d464014d793ad67a1b6e39e5c4e51a29dfe87e1f5c3e8c109201d3cb2c02',
    'guards': '017f3dca900383d0ca54117457c3610c87557b8d234ac33542838ae1730c9102',
}
PATHS = {'conker/src/game_83300.c': 'owner', 'conker/progress.csv': 'progress',
    'conker/retail_word_patches.us.csv': 'guards'}


def fixture(root, stage, key):
    out = root / source.BUILD
    data = (out / (stage + '-' + key)).read_bytes()
    digest = AFTER[key] if stage == 'after' else json.loads((out / 'baseline.json').read_text())[key]
    assert hashlib.sha256(data).hexdigest() == digest, 'Modified notification fixture: ' + key
    return data


def previous_input(current, path, root):
    current = codec_refill_checkpoint.previous_input(current, path, root)
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
        data = codec_refill_checkpoint.previous_input((root / path).read_bytes(), path, root)
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected installed notification input: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root, 'after', key) == data
