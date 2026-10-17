"""Recognize only the first complete scan owner, guard and image successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_sequence_event_scan as source
from tools.experiments.game_sequence_event_scan_installation import BUILD

AFTER=dict(elf='4e04f42dd4676fda3fb4296e755a43705c4ee9c0bed6de65b9750dfca3b29ec3',
    view_list_caller_owner='dd6d6bebb1afad7586f71e5a00a7e057d677aa51864e38ea96291e1b1806c4a7',
    guards='5084330509403cb54c534e06be40b8417b97e95addf3dd362f843e4235b58b35')
PATHS={source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data=(root/BUILD/(stage+'-'+key)).read_bytes()
    wanted=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest()==wanted,'Changed event scan fixture: '+key
    return data


def previous_input(current,path,root):
    from tools.tests import color_state_submit_checkpoint as successor
    current=successor.previous_input(current,path,root)
    relative=Path(path).as_posix();prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix):relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key in AFTER and hashlib.sha256(current).hexdigest()==AFTER[key]:return fixture(root,'before',key)
    return current


def freeze_after(root):
    from tools.tests import color_state_submit_checkpoint as successor
    for relative,key in PATHS.items():
        data=successor.previous_input((root/relative).read_bytes(),relative,root)
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected event scan successor: '+key
        target=root/BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        assert fixture(root,'after',key)==data
