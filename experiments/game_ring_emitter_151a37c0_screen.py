"""Read-only complete-C screen, with a deliberately uncredited extra word."""
from pathlib import Path
import hashlib,json,os,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
OUT=ROOT/'conker/build/game-next-151a37c0-private/setup-screen'
FROZEN=OUT/'input-baseline-v2'
PIN=json.loads(Path(__file__).with_name('game_ring_emitter_151a37c0_screen_manifest.json').read_text())
NAME,SOURCE,ENTRY,ROM=PIN['name'],PIN['source'],PIN['entry'],PIN['rom']
def recover(before,rejected=False):
 stub='s32 func_151A37C0() {\n    return 0;\n}';assert before.count(stub)==1
 return before.replace(stub,PIN['rejected_replacement' if rejected else 'replacement'])
def check_inputs():
 record=json.loads((FROZEN/'fingerprints.json').read_text())
 for name,h in record['inputs'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
 assert (ROOT/SOURCE).read_bytes()==(FROZEN/SOURCE).read_bytes()
 return len(record['inputs'])
def retail():
 raw=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+1060];assert hashlib.sha256(raw).hexdigest()==PIN['retail_sha256']
 return list(struct.unpack('>265I',raw))
def programs():
 a,ar=payload(OUT/'qualified.o',NAME);b,br=payload(OUT/'rejected.o',NAME)
 return dict(selected=bound_blob(a,ar,PIN['symbols']),rejected=bound_blob(b,br,PIN['symbols']),retail=retail())
def compile_and_check():
 check_inputs();before=(FROZEN/SOURCE).read_text();base,diag=compile_owner(ROOT,OUT,before,'baseline');assert not diag
 reports=[]
 for label,rejected in [('qualified',False),('rejected',True)]:
  obj,diag=compile_owner(ROOT,OUT,recover(before,rejected),label);assert not diag,diag
  raw,refs=payload(obj,NAME);key='rejected_raw_sha256' if rejected else 'raw_sha256';assert hashlib.sha256(raw).hexdigest()==PIN[key]
  assert len(raw)==4*(265 if rejected else 266)
  if not rejected:assert {str(k):v for k,v in refs.items()}=={k:[tuple(x) for x in v] for k,v in PIN['refs'].items()}
  assert same_functions(base,obj,(NAME,))==22 and normalized_pools(base)==normalized_pools(obj)
  words=bound_blob(raw,refs,PIN['symbols']);assert words[0]==0x27BDFEE0
  reports.append(dict(label=label,words=len(words),frame=288,neighbors_unchanged=22,pools_unchanged=True))
 check_inputs();report=dict(owners=reports,slot_words=265,threshold_word=PIN['threshold_word'],whole_function_qualified=False,source_installed=False,c_match_credit=0)
 (OUT/'source-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
