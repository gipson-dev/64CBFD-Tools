"""Pinned inverse of the dispatcher slot/extent and one profile-selection change."""
import hashlib
from pathlib import Path

from tools.experiments import game_codec_frame_dispatch_candidates as source
from tools.tests import record_payload_constructor_checkpoint

AFTER = {
    'elf': 'c9ff4e7ec28882546f87fb159a96b0c0e1c2b8fac6de4eb58725d91eef78a3bd',
    'owner': '868215866a175a9fc063e0003eb825822e0805530149981d35791a82b366c243',
    'makefile': '838070597f76ea2f7182c158dfb6710946cfcabcb5435e994f93cdb99340e313',
    'guards': '25d0c541e1bd0ea1d537439e8ba4234ad629ee9c5405025cc0408d99f28e5b9a',
}
PATHS = {'conker/build/conker.us.elf': 'elf', 'conker/src/game_221290.c': 'owner',
    'conker/Makefile': 'makefile', 'conker/retail_word_patches.us.csv': 'guards'}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    digest = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == digest, 'Modified frame-dispatch fixture: ' + key
    return data


def previous_input(current, path, root):
    current = record_payload_constructor_checkpoint.previous_input(current, path, root)
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
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected installed frame-dispatch input: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root, 'after', key) == data
