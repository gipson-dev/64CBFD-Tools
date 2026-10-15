"""Exact-input inverse of the actor-mode source and original-table binding."""
import hashlib
from pathlib import Path

from tools.experiments import game_actor_mode_flags as source

AFTER={
    'elf':'7aee8cd7ce8738cac4b947c1cbf7fdcb5dc26a68c912255d35f6fde6633094e2',
    'actor_owner':'2ec55c83c200f3b516e2bd33958b6061bc849da39a7be95381677ac8719046b1',
    'makefile':'a05e1c51adb55493227ad4fef8eb52bcefaccc006e63eef0bd027c84966ff750',
}
PATHS={source.PATHS[key]:key for key in AFTER}


def fixture(root,stage,key):
    payload=(root/source.BUILD/(stage+'-'+key)).read_bytes()
    expected=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(payload).hexdigest()==expected,'Modified actor mode fixture: '+key
    return payload


def previous_input(current,path,root):
    relative=Path(path).as_posix()
    prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix):
        relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest()==AFTER[key]:
        return fixture(root,'before',key)
    return current


def freeze_after(root):
    for path,key in PATHS.items():
        payload=(root/path).read_bytes()
        assert hashlib.sha256(payload).hexdigest()==AFTER[key],'Unexpected installed actor mode input: '+key
        target=root/source.BUILD/('after-'+key)
        if not target.exists():
            target.write_bytes(payload)
        assert fixture(root,'after',key)==payload
