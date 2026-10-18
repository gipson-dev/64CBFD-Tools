"""Exact three-file movement successor and serial, explicit historical views."""
from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path
from unittest.mock import patch

BUILD = 'conker/build/game-actor-input-movement-install'
PATHS = {'elf': 'conker/build/conker.us.elf',
         'record_gate_owner': 'conker/src/game/generated_11FF10.c',
         'guards': 'conker/retail_word_patches.us.csv'}
BEFORE = {'elf': '245487b072c4daae7de2811ce7a50e749289a6adf7f28045c833523df36d7e60',
          'record_gate_owner': '61c0c33eaa5de4d71654ed55130706b0be467a4aaa7977b5eefc6772de19eb31',
          'guards': 'e4ab0cab925c15d1099820b414eedbd0d706ee74aeba1e366127d9c2eaf9e155'}
AFTER = {'elf': 'db5587cb50d49f0ffc3de024bfc87c234d42e499667cc26d624839f4e3bff286',
         'record_gate_owner': '0a7787b4ba8e2d190ee76e5adcd0eb23edd8ee5adbe8f2e44884f514cdd21c52',
         'guards': '3f60679be81037a4035cd35f7b87a85db8764d0ccad1d68b3695bbce6a497e9b'}
raw_read, raw_text = Path.read_bytes, Path.read_text
_active = False


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fixture(root, stage, key):
    if stage not in ('before', 'after') or key not in PATHS:
        raise ValueError('Unknown movement checkpoint member')
    data = raw_read(Path(root) / BUILD / (stage + '-' + key))
    if digest(data) != (BEFORE if stage == 'before' else AFTER)[key]:
        raise ValueError('Changed immutable movement fixture: ' + stage + '-' + key)
    return data


def relative(path, root):
    try:
        return Path(os.path.abspath(path)).relative_to(Path(os.path.abspath(root))).as_posix()
    except ValueError:
        return None


def previous_input(current, path, root):
    relative_path = relative(path, root)
    key = next((k for k, p in PATHS.items() if p == relative_path), None)
    if key is None:
        return current
    old, new = fixture(root, 'before', key), fixture(root, 'after', key)
    if current not in (old, new):
        raise ValueError('Unexpected live movement input: ' + key)
    return old


def verify(root, installed=False):
    manifest = json.loads(raw_text(Path(root) / BUILD / 'initial-prediction.json'))
    if manifest != AFTER:
        raise ValueError('Changed immutable movement prediction')
    stages = set()
    for key, path in PATHS.items():
        old, new = fixture(root, 'before', key), fixture(root, 'after', key)
        data = raw_read(Path(root) / path)
        if data == old:
            stages.add('before')
        elif data == new:
            stages.add('after')
        else:
            raise ValueError('Unexpected live movement member: ' + key)
    if len(stages) != 1 or installed and stages != {'after'}:
        raise ValueError('Mixed or uninstalled movement successor')
    return next(iter(stages))


@contextmanager
def historical_view(root):
    """Read only the exact predecessor for old research; never alter disk files."""
    global _active
    if _active:
        raise RuntimeError('Movement historical view is serial and cannot nest')
    verify(root)

    def read_bytes(path):
        return previous_input(raw_read(path), path, root)

    def read_text(path, encoding=None, errors=None, newline=None):
        if relative(path, root) not in PATHS.values():
            return raw_text(path, encoding=encoding, errors=errors, newline=newline)
        with io.TextIOWrapper(io.BytesIO(read_bytes(path)), encoding=encoding,
                              errors=errors, newline=newline) as stream:
            return stream.read()

    _active = True
    try:
        with patch.object(Path, 'read_bytes', read_bytes), patch.object(Path, 'read_text', read_text):
            yield
    finally:
        _active = False
