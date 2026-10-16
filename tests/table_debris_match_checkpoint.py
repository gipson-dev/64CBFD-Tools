"""Strict table-debris source/build/image successor for the next recovery phase."""
import hashlib
from pathlib import Path

from tools.experiments import game_table_debris_match as source

AFTER = {
    'elf': '13196f6d2e9516c7bab5b9b4ad21f68812e40da2ae48b9b8b6a8d75fe1484141',
    'edge_wrapper_owner': '9b6b76a4eb7e8c9a1751a83e7357ee0c33d7bd8d0e3a8c54dd43ed9080931e5f',
    'makefile': 'bba39f33c36fa73065ede3642013a0349d0f482fe80b6b156da172d4168c817e',
}
PATHS = {source.PATHS[k]: k for k in AFTER}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == expected, 'Changed table-debris-match fixture: ' + key
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
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected table-debris-match successor: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root, 'after', key) == data
