"""Project only the exact constructor language transition onto its prior CSV."""
import hashlib
from pathlib import Path

from tools.experiments import game_record_payload_constructor_candidates as source
from tools.tests import view_frustum_plane_checkpoint

AFTER = '005fd7682d37802a2b7591cfb023648b6a083c8df6b957bdfedd737222cad68e'
PROGRESS = 'conker/progress.csv'


def previous_input(current, path, root):
    current = view_frustum_plane_checkpoint.previous_input(current, path, root)
    relative = Path(path).as_posix()
    prefix = Path(root).as_posix() + '/'
    if relative.startswith(prefix):
        relative = relative[len(prefix):]
    if relative != PROGRESS or hashlib.sha256(current).hexdigest() != AFTER:
        return current
    source.freeze(root, root / source.BUILD)
    return (root / source.BUILD / 'before-progress').read_bytes()


def freeze_after(root):
    current = view_frustum_plane_checkpoint.previous_input((root / PROGRESS).read_bytes(), PROGRESS, root)
    assert hashlib.sha256(current).hexdigest() == AFTER, 'Unexpected constructor progress'
    source.freeze(root, root / source.BUILD)
    before = (root / source.BUILD / 'before-progress').read_bytes()
    assert current == source.expected_progress(before), 'Unexpected constructor language transition'
    target = root / source.BUILD / 'after-progress'
    if not target.exists():
        target.write_bytes(current)
    assert target.read_bytes() == current, 'Modified constructor after-progress fixture'
