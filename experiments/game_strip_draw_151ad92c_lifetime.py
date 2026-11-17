"""Strip renderer lifetime recovery; partial opening relation only."""
from pathlib import Path
import hashlib,json,os,struct,sys
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
PACKET=ROOT/'conker/build/game-next-151ad92c-private'
QUALIFICATION=PACKET/'lifetime-qualified'
FROZEN=QUALIFICATION/'baseline'
OUT=Path(os.environ.get('CBFD_STRIP_DRAW_LIFETIME_WORK',QUALIFICATION/'qualification-primary'))
assert OUT.resolve().is_relative_to((ROOT/'conker/build').resolve())
PIN=json.loads(Path(__file__).with_name('game_strip_draw_151ad92c_lifetime_manifest.json').read_text())
NAME,SOURCE,ENTRY,ROM,SIZE=[PIN[n]for n in('name','source','entry','rom','size')]
STUB='s32 func_151AD92C() {\n    return 0;\n}'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
def check_inputs():
 record=json.loads((FROZEN/'fingerprints.json').read_text());assert len(record['inputs'])==PIN['frozen_input_count']
 for name,digest in record['inputs'].items():assert sha(ROOT/name)==digest,name
 assert (ROOT/SOURCE).read_bytes()==(FROZEN/SOURCE).read_bytes()
 return len(record['inputs'])
def recover(before):
 assert before.count(STUB)==1
 return before.replace(STUB,PIN['declarations']+'\n'+PIN['body'])
def compile_and_check():
 check_inputs();OUT.mkdir(exist_ok=False);before=(FROZEN/SOURCE).read_text()
 baseline,ad=compile_owner(ROOT,OUT,before,'baseline');owner,bd=compile_owner(ROOT,OUT,recover(before),'owner')
 assert not ad and not bd,(ad,bd)
 raw,refs=payload(owner,NAME)
 assert len(raw)==PIN['raw_words']*4
 assert hashlib.sha256(raw).hexdigest()==PIN['raw_sha256']
 assert refs=={int(k):[tuple(v)for v in values]for k,values in PIN['refs'].items()}
 assert same_functions(baseline,owner,(NAME,))==32 and normalized_pools(baseline)==normalized_pools(owner)
 first=struct.unpack_from('>I',raw)[0];assert first>>16==0x27BD and -(((first&65535)^32768)-32768)==PIN['frame']
 truth=(FROZEN/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE]
 assert len(truth)==SIZE and hashlib.sha256(truth).hexdigest()==PIN['retail_sha256']
 for name,data in(('raw.bin',raw),('retail.bin',truth)):(OUT/name).write_bytes(data)
 (OUT/'body.txt').write_text(PIN['body']);(OUT/'declarations.txt').write_text(PIN['declarations'])
 report=dict(raw_words=PIN['raw_words'],retail_words=PIN['retail_words'],frame=PIN['frame'],neighbors=32,pools_unchanged=True,raw_sha256=PIN['raw_sha256'],retail_sha256=PIN['retail_sha256'],source_installed=False,c_match_credit=0)
 (OUT/'source-report.json').write_text(json.dumps(report,indent=2)+'\n');check_inputs();return report
if __name__=='__main__':print(json.dumps(compile_and_check()),flush=True)

_engine_bindings=[]
def bind_engines():
 from tools.tests import game_strip_draw_151ad92c_private_oracle as guest
 from tools.tests import game_strip_draw_151ad92c_private_caller as caller
 from tools.tests import game_strip_draw_151ad92c_private_native as native
 from tools.check_game_data_layout import load_section
 at,data=load_section(FROZEN/'conker/build/conker.us.elf','.game_data')
 assert guest.ENTRY==ENTRY and guest.data_at==at and guest.data==data
 assert not _engine_bindings
 _engine_bindings.extend((module,module.source,module.p)for module in(guest,caller,native))
 for module in(guest,caller,native):module.source=sys.modules[__name__];module.p=OUT
 return guest,caller,native
def restore_engines():
 assert len(_engine_bindings)==3
 for module,original_source,original_path in _engine_bindings:
  module.source=original_source;module.p=original_path
 assert all(module.source is original_source and module.p==original_path for module,original_source,original_path in _engine_bindings)
 _engine_bindings.clear()
