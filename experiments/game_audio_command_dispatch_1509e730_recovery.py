"""Frozen semantic audio-command recovery and complete owner qualification."""
from pathlib import Path
import hashlib,json,os
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-audio-command-dispatch-1509e730-private';BASE=OUT/'baseline';WHERE=OUT/'qualified-source-screen'
SPEC=json.loads(Path(__file__).with_name('game_audio_command_dispatch_1509e730_manifest.json').read_text())
FUNCTION,SOURCE,ENTRY,ROM=(SPEC[k]for k in('function','source','entry','rom'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def installed():return{n:sha(ROOT/n)for n in SPEC['installed_snapshot']}==SPEC['installed_snapshot']

def validate_inputs():
    snapshot={n:sha(ROOT/n)for n in SPEC['installed_snapshot']}
    previous={n:SPEC['inputs'][n]for n in snapshot}
    assert snapshot in(previous,SPEC['installed_snapshot']),snapshot
    for n,d in SPEC['inputs'].items():
        if n not in snapshot:assert sha(ROOT/n)==d,n
    return snapshot==SPEC['installed_snapshot']

def screen():
    state=validate_inputs();WHERE.mkdir(exist_ok=True)
    assert sha(BASE/SOURCE)==SPEC['inputs'][SOURCE]
    before=(BASE/SOURCE).read_text();selected=before
    for a,b in SPEC['replacements']:assert selected.count(a)==1;selected=selected.replace(a,b)
    assert hashlib.sha256(selected.encode()).hexdigest()==SPEC['installed_snapshot'][SOURCE]
    a,ad=compile_owner(ROOT,WHERE,before,'before');b,bd=compile_owner(ROOT,WHERE,selected,'candidate')
    assert not ad and not bd and same_functions(a,b,(FUNCTION,))==3,(ad,bd)
    raw,refs=payload(b,FUNCTION);assert len(raw)==368 and hashlib.sha256(raw).hexdigest()==SPEC['raw_sha256']
    pool,relocations=normalized_pools(b)['.rodata']
    assert pool==bytes(32)and [r[0]for r in relocations]==list(range(0,28,4))
    assert [r[1]for r in relocations]==[FUNCTION]*7
    assert __import__('struct').pack('>7I',*[r[2]for r in relocations]).hex()==SPEC['expected_raw_pool']
    assert normalized_pools(a)=={'.rodata':None,'.data':None}and normalized_pools(b)['.data']is None
    (WHERE/'selected-owner.c').write_text(selected)
    (WHERE/'after-diagnostics.txt').write_text('')
    r=dict(words=92,frame=32,neighbors=3,relocation_sites=len(refs),table_entries=7,source_installed=state,matching_credit=0)
    (WHERE/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');return r
