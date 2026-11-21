"""Complete filtered projection draw recovery and exact snapshot gates."""
from pathlib import Path
import hashlib,json,os,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_list_unlink_1517e134_match import bind
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-projection-filtered-draw-15035d6c-private';BASE=OUT/'baseline';WHERE=OUT/'qualified-screen'
SPEC=json.loads(Path(__file__).with_name('game_projection_filtered_draw_15035d6c_manifest.json').read_text())
FUNCTION,SOURCE,BODY,ENTRY,ROM=(SPEC[k]for k in('function','source','body','entry','rom'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def screen():
    WHERE.mkdir(parents=True,exist_ok=True)
    snapshot={n:sha(ROOT/n)for n in SPEC['installed_snapshot']}
    before_snapshot={n:SPEC['inputs'][n]for n in snapshot}
    assert snapshot in(before_snapshot,SPEC['installed_snapshot']),snapshot
    for n,d in SPEC['inputs'].items():
        if n not in snapshot:assert sha(ROOT/n)==d,n
    assert sha(BASE/SOURCE)==SPEC['inputs'][SOURCE]
    before=(BASE/SOURCE).read_text();selected=before
    for old,new in SPEC['replacements']:assert selected.count(old)==1;selected=selected.replace(old,new)
    assert hashlib.sha256(selected.encode()).hexdigest()==SPEC['installed_snapshot'][SOURCE]
    a,ad=compile_owner(ROOT,WHERE,before,'before');b,bd=compile_owner(ROOT,WHERE,selected,'candidate');assert not ad and not bd,(ad,bd)
    blob,refs=payload(b,FUNCTION);words=bind(blob,refs)
    assert hashlib.sha256(blob).hexdigest()==SPEC['raw_sha256']and json.loads(json.dumps(refs))==SPEC['raw_refs']
    assert same_functions(a,b,(FUNCTION,))==9 and normalized_pools(a)==normalized_pools(b)
    assert payload(a,'func_15035808')==payload(b,'func_15035808')
    r=dict(words=len(words),frame=(-words[0])&65535,neighbors=9,pools_unchanged=True,
        submit_placeholder_unchanged=True,source_installed=BODY in(ROOT/SOURCE).read_text(),matching_credit=0)
    (WHERE/'selected-owner.c').write_text(selected);(WHERE/'after-diagnostics.txt').write_text('')
    (WHERE/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');return r
