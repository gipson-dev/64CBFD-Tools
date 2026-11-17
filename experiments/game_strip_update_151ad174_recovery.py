"""Strip update, immutable inputs and complete owner compilation."""
from pathlib import Path
import hashlib,json,os,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
ADOPTION=ROOT/'conker/build/game-next-151ad174-private/adoption-final'
OUT=Path(os.environ.get('CBFD_STRIP_UPDATE_MATCH_WORK',str(ADOPTION/'qualification-primary')))
assert OUT.resolve().is_relative_to((ROOT/'conker/build').resolve())
FROZEN=ADOPTION/'production-baseline'
PIN=json.loads(Path(__file__).with_name('game_strip_update_151ad174_manifest.json').read_text())
NAME,SOURCE,ENTRY,ROM,SIZE=PIN['name'],PIN['source'],PIN['entry'],PIN['rom'],1976
STUB='/* Placeholder: the registered callback receives a byte-addressed record. */\nvoid func_151AD174(u8 *record) {\n}'

def recover(before):
 assert before.count(STUB)==1
 return before.replace(STUB,PIN['declarations']+'\n'+PIN['body'])

def installed():
 before=(FROZEN/SOURCE).read_text();live=(ROOT/SOURCE).read_text();assert live in(before,recover(before));return live!=before
def check_inputs():
 record=json.loads((FROZEN/'fingerprints.json').read_text());assert len(record['inputs'])==PIN['frozen_input_count'];active=installed()
 plan=json.loads((ADOPTION/'adoption-plan.json').read_text())if active else{}
 if active:assert set(plan)=={SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game/generated_1D92F0.c.o','conker/build/conker.us.elf'}
 for name,h in record['inputs'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==plan.get(name,h),name
 return len(record['inputs'])
def compile_and_check():
 check_inputs();OUT.mkdir(exist_ok=False);before=(FROZEN/SOURCE).read_text()
 a,ad=compile_owner(ROOT,OUT,before,'baseline');b,bd=compile_owner(ROOT,OUT,recover(before),'v82');assert not ad and not bd,(ad,bd)
 raw,refs=payload(b,NAME);assert len(raw)==1964 and hashlib.sha256(raw).hexdigest()==PIN['raw_sha256']
 assert refs=={int(k):[tuple(v)for v in values]for k,values in PIN['refs'].items()}
 assert same_functions(a,b,(NAME,))==32 and normalized_pools(a)==normalized_pools(b)
 truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert hashlib.sha256(truth).hexdigest()==PIN['retail_sha256']
 (OUT/'retail.bin').write_bytes(truth);(OUT/'proposed-owner.c').write_text(recover(before))
 (OUT/'declarations.txt').write_text(PIN['declarations']);(OUT/'body-v82.txt').write_text(PIN['body'])
 report=dict(raw_words=491,retail_words=494,frame=776,neighbors_unchanged=32,pools_unchanged=True,source_installed=installed(),c_match_credit=0)
 (OUT/'source-report.json').write_text(json.dumps(report,indent=2)+'\n');check_inputs();return report
if __name__=='__main__':print(json.dumps(compile_and_check()),flush=True)
