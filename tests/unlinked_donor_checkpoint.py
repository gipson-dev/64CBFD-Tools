"""Pinned inverse of the independently tested nine-draft donor transition.

Historical fixtures remain immutable. Only these exact installed inputs can
project back to the nineteen-donor checkpoint; corrupt or unknown inputs pass
through unchanged and are rejected by their existing literal-image tests.
"""
import hashlib
from pathlib import Path

from tools.experiments import game_unlinked_donor_candidates as source

BEFORE = {
    'elf': source.BASELINE_ELF,
    'makefile': source.BASELINE_MAKEFILE,
    'progress': 'c1fd11fe3c2891b50cd9c3f20ed9936e6d3c90a75b17e81c50ca45cad65526e6',
}
AFTER = {
    'elf': '24cfbd09520fff37430e861e393647d6aa3ebffe1c85286b937cdf7276b3e2de',
    'makefile': '0119037edc3851385ba315698fc671b615dec5b8ceac3ea080a47d4df31d758d',
    'progress': 'a61aacac122c1c1454c0e07138f5c43b704851031bf0cec0eb04c3a9871dce3a',
}
PATHS = {'conker/build/conker.us.elf': 'elf', 'conker/Makefile': 'makefile',
    'conker/progress.csv': 'progress'}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    expected = (BEFORE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == expected, 'Modified unlinked-donor fixture: ' + key
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
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected installed input: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root, 'after', key) == data
