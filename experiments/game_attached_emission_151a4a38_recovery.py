"""Attached-point emission callback, guarded schedule and immutable-input gates."""
from pathlib import Path
import hashlib,json,os,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.game_path_heading_turn_roles import bound_blob
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
OUT=ROOT/'conker/build/game-next-151a4a38-private/adoption'
FROZEN=OUT/'production-baseline'
PIN=json.loads(Path(__file__).with_name('game_attached_emission_151a4a38_manifest.json').read_text())
NAME,SOURCE,ENTRY,ROM,SIZE=PIN['name'],PIN['source'],PIN['entry'],PIN['rom'],680

def symbols():return dict(PIN['symbols'])
def recover(before):
 stub='s32 func_151A4A38() {\n    return 0;\n}'
 assert before.count(stub)==1
 return before.replace(stub,PIN['replacement'])
def installed():
 before=(FROZEN/SOURCE).read_text();live=(ROOT/SOURCE).read_text()
 assert live in(before,recover(before));return live!=before
def check_inputs():
 record=json.loads((FROZEN/'fingerprints.json').read_text());active=installed()
 plan=json.loads((OUT/'adoption-plan.json').read_text())if active else{}
 if active:assert set(plan)=={SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game/generated_1D0840.c.o','conker/build/conker.us.elf'}
 for name,h in record['inputs'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==plan.get(name,h),name
 return len(record['inputs'])
def retail():
 raw=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE]
 assert hashlib.sha256(raw).hexdigest()==PIN['retail_sha256']
 return list(struct.unpack('>170I',raw))
def compile_and_check():
 check_inputs();before=(FROZEN/SOURCE).read_text();after=recover(before)
 a,ad=compile_owner(ROOT,OUT,before,'baseline');b,bd=compile_owner(ROOT,OUT,after,'qualified');assert not ad and not bd,(ad,bd)
 raw,refs=payload(b,NAME);assert hashlib.sha256(raw).hexdigest()==PIN['raw_sha256']
 assert {str(k):v for k,v in refs.items()}=={k:[tuple(v)for v in rs]for k,rs in PIN['refs'].items()}
 assert same_functions(a,b,(NAME,))==22 and normalized_pools(a)==normalized_pools(b)
 (OUT/'proposed-owner.c').write_text(after)
 report=dict(raw_words=170,frame=168,neighbors_unchanged=22,pools_unchanged=True,diagnostics=0,source_installed=installed(),c_match_credit=0)
 (OUT/'source-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
def programs():
 from tools.experiments.game_attached_emission_151a4a38_match import normalize
 raw,refs=payload(OUT/'qualified.o',NAME);normal,nrefs=normalize(raw,refs)
 return dict(retail=retail(),raw=bound_blob(raw,refs,symbols()),padded=bound_blob(normal,nrefs,symbols()))
if __name__=='__main__':print(json.dumps(compile_and_check()),flush=True)
