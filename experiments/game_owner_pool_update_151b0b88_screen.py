"""Uncredited owner-pool updater draft: source and immutable-input gates."""
from pathlib import Path
import hashlib,json,os,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
PACKET=ROOT/'conker/build/game-next-151b0b88-private'
FROZEN=PACKET/'baseline'
OUT=Path(os.environ.get('CBFD_OWNER_POOL_UPDATE_WORK',PACKET/'adoption/qualification-primary')).resolve()
assert OUT.is_relative_to((ROOT/'conker/build').resolve())
PIN=json.loads(Path(__file__).with_name('game_owner_pool_update_151b0b88_manifest.json').read_text())
NAME='func_151B0B88';SOURCE=PIN['source'];STUB='s32 func_151B0B88() {\n    return 0;\n}'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def check_inputs():
 pins=json.loads((FROZEN/'fingerprints.json').read_text())['inputs'];assert len(pins)==PIN['frozen_inputs']
 for name,h in pins.items():assert sha(ROOT/name)==h and sha(FROZEN/name)==h,name
 return len(pins)
def qualify_source():
 check_inputs();OUT.mkdir(exist_ok=False)
 before=(FROZEN/SOURCE).read_text();assert before.count(STUB)==1 and (ROOT/SOURCE).read_text()==before
 proposed=before.replace(STUB,PIN['declarations']+'\n'+PIN['body'])
 baseline,diagnostics=compile_owner(ROOT,OUT,before,'baseline');assert not diagnostics
 obj,diagnostics=compile_owner(ROOT,OUT,proposed,'byte-pre');assert not diagnostics
 raw,refs=payload(obj,NAME)
 expected={int(k):[tuple(v)for v in values]for k,values in PIN['refs'].items()}
 assert len(raw)==1556 and hashlib.sha256(raw).hexdigest()==PIN['raw_sha256'] and refs==expected
 assert (struct.unpack_from('>I',raw)[0]&65535)==65536-312
 assert same_functions(baseline,obj,(NAME,))==15 and normalized_pools(baseline)==normalized_pools(obj)
 words=list(struct.unpack('>385I',(FROZEN/'conker/conker.us.bin').read_bytes()[0x1DE038:0x1DE63C]))
 report=dict(passes=True,raw_words=389,retail_words=len(words),frame=312,neighbors_unchanged=15,pools_unchanged=True,frozen_inputs=check_inputs(),source_installed=False,c_match_credit=0)
 (OUT/'byte-pre.body').write_text(PIN['body']);(OUT/'byte-pre.decl').write_text(PIN['declarations'])
 (OUT/'retail.bin').write_bytes(struct.pack('>385I',*words));(OUT/'source-report.json').write_text(json.dumps(report,indent=2)+'\n')
 return report
