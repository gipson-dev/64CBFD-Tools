"""Reverse only the immutable first actor-state pair successor."""
import hashlib
from pathlib import Path
from tools.experiments import game_actor_state_update as source

BUILD='conker/build/game-actor-state-update-install'
AFTER={
    'elf':'f56e3591c3c86189f630e4b8d599d8cfd7920165766e0c309a310970cd12ba6a',
    'fixed_owner':'fdd3abb10e09badd3e6e01313c83a2e786d7960e48a8bb16893f453becbfde8b',
    'halfword_checkpoint':'8525b00eb6213e43f39bd10da19d708507a9baef5dbceedd085d8f74e5fbb6aa',
    'halfword_tests':'489704bfeceedcedfd7e47c21e9ccd9c50561d3b553166a3a29920020d8889c1',
}
PATHS={source.PATHS[key]:key for key in AFTER}

def fixture(root,stage,key):
    if stage not in ('before','after') or key not in AFTER:raise AssertionError('Unknown actor-state checkpoint member')
    data=(Path(root)/BUILD/(stage+'-'+key)).read_bytes()
    if hashlib.sha256(data).hexdigest()!=(source.BASELINE if stage=='before' else AFTER)[key]:
        raise AssertionError('Changed actor-state checkpoint fixture: '+key)
    return data

def previous_input(current,path,root):
    from tools.tests import indexed_threshold_mask_checkpoint as latest
    current=latest.previous_input(current,path,root)
    relative=Path(path).as_posix();prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix):relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest()==AFTER[key]:
        if fixture(root,'after',key)!=current:raise AssertionError('Changed actor-state successor')
        return fixture(root,'before',key)
    return current

def freeze_after(root):
    if set(AFTER)!={'elf','fixed_owner','halfword_checkpoint','halfword_tests'}:
        raise ValueError('Unknown first actor-state prediction')
    for path,key in PATHS.items():
        data=(root/path).read_bytes()
        from tools.tests import indexed_threshold_mask_checkpoint as latest
        data=latest.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=AFTER[key]:raise ValueError('Unexpected actor-state successor: '+key)
        target=root/BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        if fixture(root,'after',key)!=data:raise ValueError('Changed actor-state successor fixture')
