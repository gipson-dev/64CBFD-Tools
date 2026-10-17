"""Reverse only the immutable first threshold-mask successor."""
import hashlib
from pathlib import Path
from tools.experiments import game_indexed_threshold_mask as source

BUILD='conker/build/game-indexed-threshold-mask-install'
AFTER={
    'elf':'7bdbd79a0d8f8fa6c9da685c6aca39881442eb09e5725b7d52a9fb84659c8b94',
    'record_gate_owner':'0e94d765d6767c8f39c0111dd7bc19d2fdbbc82b6f2fb3c2cd05587d2e569349',
    'actor_state_checkpoint':'f9bea308ec9ea1b540ff00af730cd3562f2839a8571960d7561de1a9ff347912',
    'actor_state_tests':'19ddda4cca549f9712386da99ead9d042e6f96960b7cf11b01e576627fa2c931',
    'record_gate_recovery':'7aa3f8f5baf75f09d98afb00fb744db68c8fe8575f46c29ea4689e893d451a1c',
    'record_gate_tests':'101e4f2dd8305676ff49754460f1f32d3b6f153d7f59ea540faebc246a3b5dec',
}
PATHS={source.PATHS[key]:key for key in AFTER}


def fixture(root,stage,key):
    if stage not in ('before','after') or key not in AFTER:raise AssertionError('Unknown threshold-mask checkpoint member')
    data=(Path(root)/BUILD/(stage+'-'+key)).read_bytes()
    if hashlib.sha256(data).hexdigest()!=(source.BASELINE if stage=='before' else AFTER)[key]:
        raise AssertionError('Changed threshold-mask checkpoint fixture: '+key)
    return data


def previous_input(current,path,root):
    from tools.tests import actor_scale_timer_checkpoint as latest
    current=latest.previous_input(current,path,root)
    relative=Path(path).as_posix();prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix):relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest()==AFTER[key]:
        if fixture(root,'after',key)!=current:raise AssertionError('Changed threshold-mask successor')
        return fixture(root,'before',key)
    return current


def freeze_after(root):
    if set(AFTER)!={'elf','record_gate_owner','actor_state_checkpoint','actor_state_tests','record_gate_recovery','record_gate_tests'}:
        raise ValueError('Unknown first threshold-mask prediction')
    for path,key in PATHS.items():
        data=(root/path).read_bytes()
        from tools.tests import actor_scale_timer_checkpoint as latest
        data=latest.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=AFTER[key]:raise ValueError('Unexpected threshold-mask successor: '+key)
        target=root/BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        if fixture(root,'after',key)!=data:raise ValueError('Changed threshold-mask successor fixture')
