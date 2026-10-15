"""Exact-input inverse of the qualified projection family installation."""
import hashlib
from pathlib import Path

from tools.experiments import game_view_projection_family as source

AFTER = {
    'elf': '03db1e761d60ffc85ded9fb702ea53720b7c1bdeec97cbf00f34eae3dc7677d7',
    'owner': '02bdc24e7b996e207b664045d0ed1107cf2d8eb752b0a8f5eff90fe59e3a3f0b',
    'parent': 'eb3b52178dea347045168a4d261d95b830cad348dae3afa7f298500eed4dfc0c',
    'guards': 'b83e74a2f547c1274f9763a6afea8aa82781e338949247cea91eb63d36fc984a',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    digest = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == digest, 'Modified projection family fixture: ' + key
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
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected installed projection family input: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root, 'after', key) == data
