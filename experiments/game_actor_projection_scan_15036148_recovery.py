"""Complete typed actor projection scan and exact snapshot/ABI gates."""
from pathlib import Path
import hashlib,json,os,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-actor-projection-scan-15036148-private';BASE=OUT/'baseline';WHERE=OUT/'qualified-screen'
SPEC=json.loads(Path(__file__).with_name('game_actor_projection_scan_15036148_manifest.json').read_text())
FUNCTION,SOURCE,CALLER,BODY,ENTRY,ROM=(SPEC[k]for k in('function','source','caller','body','entry','rom'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def input_matches(snapshot,name,digest):
    if digest==SPEC['inputs'][name]:return True
    return any(entry['snapshot']==snapshot and entry['inputs'].get(name)==digest
        for entry in SPEC.get('compatible_input_snapshots',[]))
def bind(raw,refs,code_shift=0,data_shift=0):
    anchors={n:(0x80097D74 if n=='.rodata'else int(n.split('_')[1],16))+(code_shift if n.startswith('func_')else data_shift)for rs in refs.values()for _,n in rs}
    return tuple(bound_blob(raw,refs,anchors))
def screen():
    WHERE.mkdir(parents=True,exist_ok=True)
    snapshot={n:sha(ROOT/n)for n in SPEC['installed_snapshot']}
    before_snapshot={n:SPEC['inputs'][n]for n in snapshot}
    assert snapshot in([before_snapshot,SPEC['installed_snapshot']]+SPEC.get('compatible_installed_snapshots',[])),snapshot
    for n,d in SPEC['inputs'].items():
        if n not in snapshot:assert input_matches(snapshot,n,sha(ROOT/n)),n
    def frozen(n):
        assert sha(BASE/n)==SPEC['inputs'][n],n
        return(BASE/n).read_text()
    before=frozen(SOURCE);selected=before
    for old,new in SPEC['replacements']:assert selected.count(old)==1;selected=selected.replace(old,new)
    assert hashlib.sha256(selected.encode()).hexdigest()==SPEC['installed_snapshot'][SOURCE]
    a,ad=compile_owner(ROOT,WHERE,before,'before');b,bd=compile_owner(ROOT,WHERE,selected,'candidate');assert not ad and not bd,(ad,bd)
    blob,refs=payload(b,FUNCTION);words=bind(blob,refs)
    assert hashlib.sha256(blob).hexdigest()==SPEC['raw_sha256']and json.loads(json.dumps(refs))==SPEC['raw_refs']
    assert same_functions(a,b,(FUNCTION,'func_15035808'))==8
    assert normalized_pools(a)=={'.rodata':None,'.data':None}
    assert normalized_pools(b)=={'.rodata':(bytes.fromhex('c61c4000000000000000000000000000'),()),'.data':None}
    h,hr=payload(b,'func_15035808');old_h,old_hr=payload(a,'func_15035808')
    assert not hr and not old_hr and h==bytes.fromhex('afa40000afa50004afa60008afa7000c')+old_h
    old=frozen(CALLER);revised=old
    for before_text,after_text in SPEC['caller_replacements']:assert revised.count(before_text)==1;revised=revised.replace(before_text,after_text)
    assert hashlib.sha256(revised.encode()).hexdigest()==SPEC['installed_snapshot'][CALLER]
    ca,cd=compile_owner(ROOT,WHERE,old,'caller-before');cb,cbd=compile_owner(ROOT,WHERE,revised,'caller-after')
    assert cd.replace('caller-before','caller-input')==cbd.replace('caller-after','caller-input')and cd.count('Warning 712:')==3
    assert same_functions(ca,cb,())==16 and normalized_pools(ca)==normalized_pools(cb)
    truth=struct.unpack_from('>112I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM)
    r=dict(words=len(words),frame=(-words[0])&65535,neighbors=8,helper_words=7,helper_still_unrecovered=True,
        differences=sum(x!=y for x,y in zip(words,truth)),verified_pool=True,caller_functions_unchanged=16,
        unchanged_caller_Warning_712_count=3,source_installed=BODY in(ROOT/SOURCE).read_text(),matching_credit=0)
    (WHERE/'selected-owner.c').write_text(selected);(WHERE/'selected-caller.c').write_text(revised)
    (WHERE/'after-diagnostics.txt').write_text('');(WHERE/'caller-after-diagnostics.txt').write_text(cbd)
    (WHERE/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');return r
