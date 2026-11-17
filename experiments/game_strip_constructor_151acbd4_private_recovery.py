"""Immutable private strip-constructor source and complete-owner checks."""
from pathlib import Path
import hashlib,json,os
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
PACKET=ROOT/'conker/build/game-next-151acbd4-private';QUALIFICATION=PACKET/'qualification'
FROZEN=PACKET/'qualification-baseline'
OUT=Path(os.environ.get('CBFD_STRIP_PRIVATE_WORK',str(QUALIFICATION/'qualification-primary')))
assert OUT.resolve().is_relative_to((ROOT/'conker/build').resolve())
PIN=json.loads(Path(__file__).with_name('game_strip_constructor_151acbd4_private_manifest.json').read_text())
NAME,SOURCE,ENTRY,ROM,SIZE=PIN['name'],PIN['source'],PIN['entry'],PIN['rom'],PIN['size']
def check_inputs():
 record=json.loads((FROZEN/'fingerprints.json').read_text())['inputs']
 for name,h in record.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
 assert 's32 func_151ACBD4() {\n    return 0;\n}'in(ROOT/SOURCE).read_text()
 return len(record)
def compile_and_check():
 check_inputs();OUT.mkdir(exist_ok=False);before=(FROZEN/SOURCE).read_text();stub='s32 func_151ACBD4() {\n    return 0;\n}';assert before.count(stub)==1
 baseline,bd=compile_owner(ROOT,OUT,before,'baseline');assert not bd,bd
 for label,row in PIN['variants'].items():
  source=before.replace(stub,PIN['declarations']+'\n'+row['body']);obj,diagnostics=compile_owner(ROOT,OUT,source,label);assert not diagnostics,diagnostics
  raw,refs=payload(obj,NAME);assert len(raw)==1544 and hashlib.sha256(raw).hexdigest()==row['raw_sha256']
  assert same_functions(baseline,obj,(NAME,))==32 and normalized_pools(baseline)==normalized_pools(obj)
  (OUT/('body-'+label+'.txt')).write_text(row['body'])
 truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert hashlib.sha256(truth).hexdigest()==PIN['retail_sha256'];(OUT/'retail.bin').write_bytes(truth)
 (OUT/'declarations.txt').write_text(PIN['declarations']);check_inputs()
 report=dict(raw_words=386,retail_words=360,frame=64,neighbors_unchanged=32,pools_unchanged=True,variants=list(PIN['variants']),source_installed=False,c_match_credit=0)
 (OUT/'source-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
