"""Complete record draw C recovery and exact before/installed snapshot gates."""
from pathlib import Path
from tools.experiments.game_list_historical_image import qualified_input_context
import hashlib,json,os,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_list_unlink_1517e134_match import bind
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-projection-record-draw-15035fe8-private';BASE=OUT/'baseline';WHERE=OUT/'qualified-screen'
SPEC=json.loads(Path(__file__).with_name('game_projection_record_draw_15035fe8_manifest.json').read_text())
SOURCE=SPEC['source'];CALLER=SPEC['caller'];FUNCTION=SPEC['function'];BODY=SPEC['body'];ENTRY=SPEC['entry'];ROM=SPEC['rom']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def screen():
    extra=qualified_input_context(ROOT,SOURCE,SPEC)
    WHERE.mkdir(parents=True,exist_ok=True)
    snapshot={n:sha(ROOT/n)for n in SPEC['installed_snapshot']}
    before_snapshot={n:SPEC['inputs'][n]for n in snapshot}
    assert snapshot in([before_snapshot,SPEC['installed_snapshot']]+SPEC.get('compatible_installed_snapshots',[])),snapshot
    for n,d in SPEC['inputs'].items():
        if n not in snapshot:assert sha(ROOT/n)==extra.get(n,d),n
    def frozen(n):
        assert sha(BASE/n)==SPEC['inputs'][n],n
        return(BASE/n).read_text()
    before=frozen(SOURCE);selected=before
    for old,new in SPEC['replacements']:assert selected.count(old)==1;selected=selected.replace(old,new)
    assert hashlib.sha256(selected.encode()).hexdigest()==SPEC['installed_snapshot'][SOURCE]
    a,ad=compile_owner(ROOT,WHERE,before,'before');b,bd=compile_owner(ROOT,WHERE,selected,'candidate');assert not ad and not bd,(ad,bd)
    blob,refs=payload(b,FUNCTION);words=bind(blob,refs)
    assert hashlib.sha256(blob).hexdigest()==SPEC['raw_sha256']and json.loads(json.dumps(refs))==SPEC['raw_refs']
    neighbors=same_functions(a,b,(FUNCTION,));assert neighbors==9 and normalized_pools(a)==normalized_pools(b)
    old=frozen(CALLER);revised=old
    for before_text,after_text in SPEC['caller_replacements']:assert revised.count(before_text)==1;revised=revised.replace(before_text,after_text)
    assert hashlib.sha256(revised.encode()).hexdigest()==SPEC['installed_snapshot'][CALLER]
    ca,cd=compile_owner(ROOT,WHERE,old,'caller-before');cb,cbd=compile_owner(ROOT,WHERE,revised,'caller-typed')
    assert cd.replace('caller-before','caller-input')==cbd.replace('caller-typed','caller-input')and cd.count('Warning 712:')==3
    assert same_functions(ca,cb,())==16 and normalized_pools(ca)==normalized_pools(cb)
    truth=struct.unpack_from('>88I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM)
    report=dict(words=len(words),frame=(-words[0])&65535,parameters_offset=84,neighbors=neighbors,pools_unchanged=True,
                differences=sum(x!=y for x,y in zip(words,truth))+abs(len(words)-len(truth)),caller_functions_unchanged=16,
                unchanged_caller_Warning_712_count=3,diagnostics='',source_installed=BODY in(ROOT/SOURCE).read_text(),matching_credit=0)
    (WHERE/'selected-owner.c').write_text(selected);(WHERE/'selected-caller.c').write_text(revised)
    (WHERE/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');return report
