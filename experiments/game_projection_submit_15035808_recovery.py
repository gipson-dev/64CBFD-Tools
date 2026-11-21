"""Frozen projection submission source, ABI and owner qualification."""
from pathlib import Path
import hashlib,json,os
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_c_object as pc,pad_generated_object as pg
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-projection-submit-15035808-private';BASE=OUT/'baseline';WHERE=OUT/'qualified-screen'
SPEC=json.loads(Path(__file__).with_name('game_projection_submit_15035808_manifest.json').read_text())
FUNCTION,SOURCE,ENTRY,ROM=(SPEC[k]for k in('function','source','entry','rom'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def original_assembly():
    text=(ROOT/'conker/asm/61D10.s').read_text();a=text.index('glabel '+FUNCTION+'\n');b=text.index('endlabel '+FUNCTION,a)+len('endlabel '+FUNCTION)
    return text[a:b]
def screen():
    WHERE.mkdir(exist_ok=True)
    snapshot={n:sha(ROOT/n)for n in SPEC['installed_snapshot']};previous={n:SPEC['inputs'][n]for n in snapshot}
    assert snapshot in([previous,SPEC['installed_snapshot']]+SPEC.get('compatible_installed_snapshots',[])),snapshot
    for n,d in SPEC['inputs'].items():
        if n not in snapshot:assert sha(ROOT/n)==d,n
    before=(BASE/SOURCE).read_text();assert sha(BASE/SOURCE)==SPEC['inputs'][SOURCE];selected=before
    for old,new in SPEC['replacements']:assert selected.count(old)==1;selected=selected.replace(old,new)
    assert hashlib.sha256(selected.encode()).hexdigest()==SPEC['installed_snapshot'][SOURCE]
    a,ad=compile_owner(ROOT,WHERE,before,'before');b,bd=compile_owner(ROOT,WHERE,selected,'candidate');assert not ad and not bd,(ad,bd)
    raw,refs=payload(b,FUNCTION);plan=SPEC['schedule_plan']
    assert hashlib.sha256(raw).hexdigest()==plan['source_raw_sha256']and json.loads(json.dumps(refs))==plan['source_refs']
    assert same_functions(a,b,(FUNCTION,))==9 and normalized_pools(a)==normalized_pools(b)
    c=SPEC['caller'];old,new=SPEC['caller_replacement'];text=(BASE/c).read_text();assert text.count(old)==1
    after=text.replace(old,new);assert hashlib.sha256(after.encode()).hexdigest()==SPEC['installed_snapshot'][c]
    ca,cad=compile_owner(ROOT,WHERE,text,'caller-before');cb,cbd=compile_owner(ROOT,WHERE,after,'caller-after')
    assert not cad and not cbd and same_functions(ca,cb,())==28 and normalized_pools(ca)==normalized_pools(cb)
    assert pc.emit_padded_assembly(ca,ROOT/'conker/retail_layout.us.txt','generated_CDE80')==pc.emit_padded_assembly(cb,ROOT/'conker/retail_layout.us.txt','generated_CDE80')
    assert pg.emit_padded_assembly(ca,ROOT/'conker/asm/CDE80.s',filename='generated_CDE80')==pg.emit_padded_assembly(cb,ROOT/'conker/asm/CDE80.s',filename='generated_CDE80')
    (WHERE/'selected-owner.c').write_text(selected);(WHERE/'selected-caller.c').write_text(after);(WHERE/'after-diagnostics.txt').write_text('')
    r=dict(words=345,frame=216,neighbors=9,caller_functions=28,pools_unchanged=True,caller_padded_assembly_unchanged=True,
        source_installed=snapshot==SPEC['installed_snapshot'],matching_credit=0)
    (WHERE/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');return r
