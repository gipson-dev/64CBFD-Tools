"""Accept only the first independently predicted complete burst successor."""
import hashlib
from pathlib import Path
from tools.experiments import game_transition_burst_match as source

BUILD='conker/build/game-transition-burst-install'
AFTER={
    'elf':'3a166821cbf72bc1d0576277659ee0079e896cae66b7f33f1aa15a019a47308a',
    'tile_owner':'0ed6b7d1ac20065bb63096427a011a389901654bc9f2ae99f369c399ea2314ca',
    'guards':'fc6e9c02547bebd537ab093029b210586e4e54e0342ce415845e37eb4cfbddf5',
    'makefile':'ebd94346464987605699e4709194a11c08e248f02d94a400580690e0bdda7c69',
    'child_checkpoint':'4d7324b83d63ad1c814507f980783d6c3f70d29f2d63536326f9dd11aefe6190',
}
PATHS={source.PATHS[key]:key for key in AFTER}


def fixture(root,stage,key):
    data=(Path(root)/BUILD/(stage+'-'+key)).read_bytes()
    if hashlib.sha256(data).hexdigest()!=(source.BASELINE if stage=='before' else AFTER)[key]:
        raise AssertionError('Changed burst checkpoint fixture: '+key)
    return data


def previous_input(current,path,root):
    from tools.tests import link_event_checkpoint as latest
    current=latest.previous_input(current,path,root)
    relative=Path(path).as_posix();prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix):relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest()==AFTER[key]:
        if fixture(root,'after',key)!=current:raise AssertionError('Changed burst successor')
        return fixture(root,'before',key)
    return current


def freeze_after(root):
    if set(AFTER)!={'elf','tile_owner','guards','makefile','child_checkpoint'}:
        raise ValueError('First burst prediction is not banked')
    for path,key in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=AFTER[key]:raise ValueError('Unexpected burst successor: '+key)
        target=root/BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        if fixture(root,'after',key)!=data:raise ValueError('Changed burst successor fixture')
