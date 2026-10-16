"""Recognize only the measured two-row graphics/profile/guard successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_view_list_setup as source

AFTER = dict(elf='3fa2606e9667487ba4196ca1cd897616c0dceea23fa7212cb5452d24315ac537',
    frustum_owner='679a3c4d3e37373ca363238cfd6f4bd86c5ff349be9872ad936e342cf44a88eb',
    guards='23a0277187ad0fb321d436abc593093eb6dea2afa9013ae2c6aea12f1fe5a6b6',
    makefile='618ebdb771471685b190883b98067025d4b0784d2d0c9ce6a22a8acef5f3f180')
PATHS = {source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data=(root/source.BUILD/(stage+'-'+key)).read_bytes()
    wanted=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest()==wanted,'Changed view-list setup fixture: '+key
    return data


def previous_input(current,path,root):
    relative=Path(path).as_posix();prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix):relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest()==AFTER[key]:return fixture(root,'before',key)
    return current


def freeze_after(root):
    for relative,key in PATHS.items():
        data=(root/relative).read_bytes()
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected view-list setup successor: '+key
        target=root/source.BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        assert fixture(root,'after',key)==data
