"""Reverse only the declared immutable owner-burst installation successor."""
import hashlib
import json
from pathlib import Path
from tools.experiments import game_owner_burst_match as source

BUILD='conker/build/game-owner-burst-install'
MEMBERS=('elf','record_gate_owner','guards','makefile','owner_burst_2d14_recovery','scale_timer_checkpoint',
    'scale_timer_tests','owner_burst_2d14_tests','owner_burst_2d14_frame_tests','owner_burst_2d14_local_tests')
AFTER={
    'elf':'245487b072c4daae7de2811ce7a50e749289a6adf7f28045c833523df36d7e60',
    'record_gate_owner':'61c0c33eaa5de4d71654ed55130706b0be467a4aaa7977b5eefc6772de19eb31',
    'guards':'e4ab0cab925c15d1099820b414eedbd0d706ee74aeba1e366127d9c2eaf9e155',
    'makefile':'a6e92d90cdeb8c65e7d1ff57f6603ea4f0e5bee6c09d5a028a51a1e0e369bfd6',
    'owner_burst_2d14_recovery':'dddc138e961302080c3aedfaa21d3ada325d21d41d691eccbddc5a7643b53c0c',
    'scale_timer_checkpoint':'4291b3681dea1afb0e48f34b8c7efdadb99dbfad3d276921877d22c55f3faf13',
    'scale_timer_tests':'1122daa4e1fc3311658db1c1dff4460918b114fd81effa8a3a1a5780e6263aa5',
    'owner_burst_2d14_tests':'d5f19e572ab32761dd8715815a4876dac509f6cdd582eb303d9de67b9304ec41',
    'owner_burst_2d14_frame_tests':'935ac68e48730ae0271b661e508523867d18c541fecac5c8148660de46968b45',
    'owner_burst_2d14_local_tests':'d2e7093d2374e53e4e47d97d730709c59412d097c7baceddca31fb9fa0b0a317',
}
PATHS={source.PATHS[key]:key for key in AFTER}


def fixture(root,stage,key):
    if stage not in ('before','after') or key not in MEMBERS:raise AssertionError('Unknown burst checkpoint member')
    data=(Path(root)/BUILD/(stage+'-'+key)).read_bytes()
    if hashlib.sha256(data).hexdigest()!=(source.BASELINE if stage=='before' else AFTER)[key]:
        raise AssertionError('Changed burst checkpoint fixture: '+key)
    return data


def previous_input(current,path,root):
    relative=Path(path).as_posix();prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix):relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest()==AFTER[key]:
        if fixture(root,'after',key)!=current:raise AssertionError('Changed burst successor')
        return fixture(root,'before',key)
    return current


def freeze_after(root):
    if set(AFTER)!=set(MEMBERS):raise ValueError('Incomplete first burst successor prediction')
    out=root/BUILD
    if json.loads((out/'initial-prediction.json').read_text())!=AFTER:raise ValueError('Changed first burst prediction')
    pending={}
    for key in MEMBERS:
        path=source.PATHS[key];data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=AFTER[key]:raise ValueError('Unexpected burst successor: '+key)
        fixture(root,'before',key);pending[key]=data
    for key,data in pending.items():
        target=out/('after-'+key)
        if not target.exists():target.write_bytes(data)
        if fixture(root,'after',key)!=data:raise ValueError('Changed burst successor fixture: '+key)
