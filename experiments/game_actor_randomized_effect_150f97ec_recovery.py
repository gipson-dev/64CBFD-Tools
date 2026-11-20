"""Complete typed actor effect C recovery; raw source remains 88 words."""
from pathlib import Path
import hashlib,json,os,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_list_unlink_1517e134_match import bind
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-actor-randomized-effect-150f97ec-private';BASE=OUT/'baseline';WHERE=OUT/'qualified-screen'
SPEC=json.loads(Path(__file__).with_name('game_actor_randomized_effect_150f97ec_manifest.json').read_text())
SOURCE=SPEC['source'];BODY=SPEC['body'];PREAMBLE=SPEC['preamble'];FUNCTION=SPEC['function'];ENTRY=SPEC['entry'];ROM=SPEC['rom']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def screen():
    WHERE.mkdir(parents=True,exist_ok=True)
    actual=(sha(ROOT/SOURCE),sha(ROOT/'conker/retail_word_patches.us.csv'))
    accepted=[(SPEC['inputs'][SOURCE],SPEC['inputs']['conker/retail_word_patches.us.csv']),(SPEC['selected_source_sha256'],SPEC['guards_after_sha256'])]
    accepted += [(r['source_sha256'],r['guards_sha256'])for r in SPEC.get('compatible_installed_snapshots',[])]
    assert actual in accepted,actual
    for n,d in SPEC['inputs'].items():
        if n not in(SOURCE,'conker/retail_word_patches.us.csv'):assert sha(ROOT/n)==d,n
    before=(BASE/SOURCE).read_text();assert sha(BASE/SOURCE)==SPEC['inputs'][SOURCE]
    stub='s32 func_150F97EC() {\n    return 0;\n}';assert before.count(stub)==1
    selected=before.replace(stub,SPEC['replacement']);assert hashlib.sha256(selected.encode()).hexdigest()==SPEC['selected_source_sha256']
    a,ad=compile_owner(ROOT,WHERE,before,'before');b,bd=compile_owner(ROOT,WHERE,selected,'candidate');assert not ad and not bd,(ad,bd)
    blob,refs=payload(b,FUNCTION);words=bind(blob,refs)
    assert hashlib.sha256(blob).hexdigest()==SPEC['raw_sha256']and json.loads(json.dumps(refs))==SPEC['raw_refs']
    truth=struct.unpack_from('>89I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM)
    report=dict(words=len(words),frame=(-words[0])&65535,differences=sum(x!=y for x,y in zip(words,truth))+abs(len(words)-len(truth)),
        neighbors=same_functions(a,b,(FUNCTION,)),pools_unchanged=normalized_pools(a)==normalized_pools(b),diagnostics='',source_installed=BODY in(ROOT/SOURCE).read_text(),matching_credit=0)
    (WHERE/'selected-owner.c').write_text(selected);(WHERE/'after-diagnostics.txt').write_text('');(WHERE/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');return report
