"""Reverse only the first predicted actor-update successor for archived fixtures."""
import hashlib
from pathlib import Path
from tools.experiments import game_actor_counter_motion as source

BUILD='conker/build/game-actor-counter-motion-install'
AFTER={
    'elf':'b62c85c1a8e02733790c827821229caaa487c0776bf87318a337c9f8142248eb',
    'motion_owner':'be8ffe75cccbc64eda042e26043bbbe77f0b3d382dd83ab80163e177309977e2',
    'reveal_checkpoint':'bad5ab740ec5a027b4ed84c97183b8c73503f8fe8a8d780baea15fcf06aade8c',
    'white_source':'66d6dd8d27da416a93d7d19fc00222ef1dd9b2186ef01934ad244ee36fec5087',
    'white_tests':'c72cca017aa7d94c471a4ba300f3fcba7e1dfeae81d5f74ccd507c11968def1c',
    'reveal_tests':'b603fb6a11ad180c178815d71a1ca5eafabcd438d0e7dcf84162ad3779b2989e',
}
PATHS={source.PATHS[key]:key for key in AFTER}


def fixture(root,stage,key):
    if stage not in ('before','after') or key not in AFTER:raise AssertionError('Unknown actor counter-motion checkpoint member')
    data=(Path(root)/BUILD/(stage+'-'+key)).read_bytes()
    if hashlib.sha256(data).hexdigest()!=(source.BASELINE if stage=='before' else AFTER)[key]:
        raise AssertionError('Changed actor counter-motion checkpoint fixture: '+key)
    return data


def previous_input(current,path,root):
    relative=Path(path).as_posix();prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix):relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest()==AFTER[key]:
        if fixture(root,'after',key)!=current:raise AssertionError('Changed actor counter-motion successor')
        return fixture(root,'before',key)
    return current


def freeze_after(root):
    if set(AFTER)!={'elf','motion_owner','reveal_checkpoint','white_source','white_tests','reveal_tests'}:
        raise ValueError('Unknown first actor counter-motion prediction')
    for path,key in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=AFTER[key]:raise ValueError('Unexpected actor counter-motion successor: '+key)
        target=root/BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        if fixture(root,'after',key)!=data:raise ValueError('Changed actor counter-motion successor fixture')
