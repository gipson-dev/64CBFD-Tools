"""Closed refill slot/extent/profile inverse for immutable historical checks."""
import hashlib
from pathlib import Path

from tools.experiments import game_codec_input_refill_candidates as source

AFTER = {
    'elf': 'a89a94186b0a4d2c0eedf36f927980489aa4e13783a642baf221de4760d11f18',
    'owner': 'd4ff5335ad0b03f85a580edd24cd6ab0ab2d6f01220d14a16c3ea6c8438cfa45',
    'makefile': 'e773e5d536287a688d5c265bc6e82f667cd2e1d24e0f1747ebc47bbdb4de449c',
    'guards': '0154601eeb05171a8af1c2ce21e4d322b0ec338142d6c0a38ea7c4bd8dd8ca24',
}
PATHS = {'conker/build/conker.us.elf': 'elf', 'conker/src/game_221290.c': 'owner',
    'conker/Makefile': 'makefile', 'conker/retail_word_patches.us.csv': 'guards'}


def fixture(root, stage, key):
    label = 'final-owner' if stage == 'after' and key == 'owner' else key
    data = (root / source.BUILD / (stage + '-' + label)).read_bytes()
    digest = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == digest, 'Modified codec refill fixture: ' + key
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
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected installed codec refill input: ' + key
        target = root / source.BUILD / ('after-' + ('final-owner' if key == 'owner' else key))
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root, 'after', key) == data
