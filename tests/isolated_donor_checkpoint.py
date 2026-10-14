"""Closed two-function transition after the independently checked draft bank."""
import hashlib
from pathlib import Path

from tools.experiments import game_isolated_donor_candidates as source
from tools.tests import commented_notification_checkpoint

BEFORE = {'elf': source.BASELINE_ELF,
    'progress': 'a61aacac122c1c1454c0e07138f5c43b704851031bf0cec0eb04c3a9871dce3a'}
AFTER = {'elf': 'bbc201571e311a6946d21093d697b0fd7c18134e861f0e162922d4952416792f',
    'progress': '05e9009f0eb5bb5e2955b02f53beb6ff9b54999599814e8e86dec5c39f62cf31'}
PATHS = {'conker/build/conker.us.elf': 'elf', 'conker/progress.csv': 'progress'}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    digest = (BEFORE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == digest, 'Modified isolated-donor fixture: ' + key
    return data


def previous_input(current, path, root):
    current = commented_notification_checkpoint.previous_input(current, path, root)
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
        data = commented_notification_checkpoint.previous_input((root / path).read_bytes(), path, root)
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected installed input: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root, 'after', key) == data
