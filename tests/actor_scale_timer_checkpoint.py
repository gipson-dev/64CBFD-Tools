"""Reverse only the immutable first scale-timer successor."""
import hashlib
from pathlib import Path
from tools.experiments import game_actor_scale_timer as source

BUILD='conker/build/game-actor-scale-timer-install'
AFTER={
    'elf':'5efb8a9f598af0712d97eaf4d0f2ab2df134e349ad16eddfeb0f75e74128b7d4',
    'record_gate_owner':'60e0bbe1882ca4a112d1bc43672a2e99a5dcf9b1f85e83196b82511817eee104',
    'guards':'8436b1f77fa3a7a99a30ff888ba6da1d06c029d5fbe5e87e291478f54dcc0d18',
    'threshold_mask_recovery':'beaa6754c273a88493154c0996a667b73432151dc8cc33a25f1bd6a568db5ae6',
    'threshold_mask_checkpoint':'bf194ef778b4b0cfd501a35f82f84b1e278ae05b81da28d6fe0f4382fdd44e50',
    'threshold_mask_tests':'0bfeff799c85eba22f7fea9512e88b6a365facf6aebe11b16139970a426f5f96',
}
# This test-only successor is separate from the immutable six-member image prediction.
FOLLOWUP={'actor_state_tests':'4d0920327677173cf21b7271fab5694cef71425814d8faa476b84df68f00e312'}
PATHS={source.PATHS[key]:key for key in (*AFTER,*FOLLOWUP)}


def fixture(root,stage,key):
    if stage not in ('before','after') or key not in (*AFTER,*FOLLOWUP):raise AssertionError('Unknown scale-timer checkpoint member')
    data=(Path(root)/BUILD/(stage+'-'+key)).read_bytes()
    if hashlib.sha256(data).hexdigest()!=(source.BASELINE if stage=='before' else {**AFTER,**FOLLOWUP})[key]:
        raise AssertionError('Changed scale-timer checkpoint fixture: '+key)
    return data


def previous_input(current,path,root):
    relative=Path(path).as_posix();prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix):relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest()=={**AFTER,**FOLLOWUP}[key]:
        if fixture(root,'after',key)!=current:raise AssertionError('Changed scale-timer successor')
        return fixture(root,'before',key)
    return current


def freeze_after(root):
    if set(AFTER)!={'elf','record_gate_owner','guards','threshold_mask_recovery','threshold_mask_checkpoint','threshold_mask_tests'}:
        raise ValueError('Unknown first scale-timer prediction')
    if set(FOLLOWUP)!={'actor_state_tests'}:raise ValueError('Unknown scale-timer test-only followup')
    for path,key in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!={**AFTER,**FOLLOWUP}[key]:raise ValueError('Unexpected scale-timer successor: '+key)
        target=root/BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        if fixture(root,'after',key)!=data:raise ValueError('Changed scale-timer successor fixture')
