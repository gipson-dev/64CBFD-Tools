"""Strip attachment recovery and immutable production-input qualification."""
from pathlib import Path
import hashlib,json,os,struct,sys
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
ADOPTION=ROOT/'conker/build/game-next-151ae3a8-private/adoption'
OUT=Path(os.environ.get('CBFD_STRIP_FOLLOW_MATCH_WORK',ADOPTION/'qualification-primary'))
assert OUT.resolve().is_relative_to((ROOT/'conker/build').resolve())
FROZEN=ADOPTION/'production-baseline'
PIN=json.loads(Path(__file__).with_name('game_strip_follow_151ae3a8_manifest.json').read_text())
NAME,SOURCE,ENTRY,ROM,SIZE=[PIN[n]for n in('name','source','entry','rom','size')]
STUB='s32 func_151AE3A8() {\n    return 0;\n}'

def recover(before):
 assert before.count(STUB)==1
 return before.replace('s32 func_151AE3A8();','void func_151AE3A8(u8 *input);').replace(STUB,PIN['declarations']+'\n'+PIN['body'])


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
 a,ad=compile_owner(ROOT,OUT,before,'baseline');b,bd=compile_owner(ROOT,OUT,recover(before),'owner');assert not ad and not bd,(ad,bd)
 raw,refs=payload(b,NAME);assert len(raw)==480 and hashlib.sha256(raw).hexdigest()==PIN['raw_sha256']
 assert refs=={int(k):[tuple(v)for v in values]for k,values in PIN['refs'].items()}
 assert same_functions(a,b,(NAME,))==32 and normalized_pools(a)==normalized_pools(b)
 first=struct.unpack_from('>I',raw)[0];assert first==0x27BDFF88
 truth=(FROZEN/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert hashlib.sha256(truth).hexdigest()==PIN['retail_sha256']
 (OUT/'retail.bin').write_bytes(truth);(OUT/'raw.bin').write_bytes(raw);(OUT/'proposed-owner.c').write_text(recover(before))
 report=dict(raw_words=120,retail_words=122,frame=120,neighbors_unchanged=32,pools_unchanged=True,source_installed=installed(),c_match_credit=0)
 (OUT/'source-report.json').write_text(json.dumps(report,indent=2)+'\n');check_inputs();return report
