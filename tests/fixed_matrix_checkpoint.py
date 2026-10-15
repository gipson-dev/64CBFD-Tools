"""Exact-input inverse of the original fixed-converter ownership correction."""
import hashlib
from pathlib import Path

from tools.experiments import game_fixed_matrix_restoration as source
from tools.tests import view_orthographic_setup_checkpoint

AFTER = {
    'elf': '7328baa3d6e02c46ba323034c3400d9644ff798d76a55cf062fff676155dacde',
    'owner': '1d486625290c9609ee6950dad7260ee7273f151527c944b08d8ac1c451b51a66',
    'assembly': '4eefb559eb0b01560a210b2bfd4826149a7aece83371ff29c6bcbd29c3b113ba',
    'progress': 'e3ea336daf5c7c20478bd705eec06b202685d29498d7797a6a546c2476211c78',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    digest = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == digest, 'Modified fixed-matrix checkpoint fixture: ' + key
    return data


def previous_input(current, path, root):
    current = view_orthographic_setup_checkpoint.previous_input(current, path, root)
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
        data = view_orthographic_setup_checkpoint.previous_input((root / path).read_bytes(), path, root)
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected installed fixed-matrix input: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root, 'after', key) == data
