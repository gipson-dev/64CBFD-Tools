"""Immutable ring predecessor and the initial, pre-install successor prediction."""
import hashlib
from pathlib import Path

from tools.experiments import game_randomized_ring_emitter as source

AFTER = {
    'elf': '42f7aaa72746fe4815290922d9aa5b907528865ec34294dd6e5d6ed936311f1c',
    'edge_wrapper_owner': '43f273ed63bb2c1a129a5c7bd95089d3d24bf8586b0965ad5ca3e8536f02f10f',
    'guards': 'fee1a24bdf16c415bcf302814da4dec0293c5883f4aad9d0fe6fe96df5dc4f6f',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == expected, 'Modified ring fixture: ' + key
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
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected ring successor: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root, 'after', key) == data
