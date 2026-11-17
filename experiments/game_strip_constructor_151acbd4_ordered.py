"""Private complete provider/return relation; no production source or guards."""
from pathlib import Path
import hashlib,json,os
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
PACKET=ROOT/'conker/build/game-next-151acbd4-private';QUALIFICATION=PACKET/'ordered-qualification'
FROZEN=PACKET/'ordered-baseline'
OUT=Path(os.environ.get('CBFD_STRIP_ORDERED_WORK',str(QUALIFICATION/'qualification-primary')))
assert OUT.resolve().is_relative_to((ROOT/'conker/build').resolve())
PIN=json.loads(Path(__file__).with_name('game_strip_constructor_151acbd4_ordered_manifest.json').read_text())
NAME,SOURCE,ENTRY,ROM,SIZE=PIN['name'],PIN['source'],PIN['entry'],PIN['rom'],PIN['size']
def check_inputs():
 inputs=json.loads((FROZEN/'fingerprints.json').read_text())['inputs']
 for name,h in inputs.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
 assert 's32 func_151ACBD4() {\n    return 0;\n}'in(ROOT/SOURCE).read_text()
 return len(inputs)
def compile_and_check():
 check_inputs();OUT.mkdir(exist_ok=False)
 before=(FROZEN/SOURCE).read_text();stub='s32 func_151ACBD4() {\n    return 0;\n}';assert before.count(stub)==1
 baseline,bd=compile_owner(ROOT,OUT,before,'baseline');assert not bd,bd
 obj,diag=compile_owner(ROOT,OUT,before.replace(stub,PIN['declarations']+'\n'+PIN['body']),'v35');assert not diag,diag
 raw,refs=payload(obj,NAME);assert len(raw)==1552 and hashlib.sha256(raw).hexdigest()==PIN['raw_sha256']
 assert same_functions(baseline,obj,(NAME,))==32 and normalized_pools(baseline)==normalized_pools(obj)
 truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert hashlib.sha256(truth).hexdigest()==PIN['retail_sha256']
 (OUT/'retail.bin').write_bytes(truth);(OUT/'declarations.txt').write_text(PIN['declarations']);(OUT/'body-v35.txt').write_text(PIN['body'])
 syms={r[1]:r[2][1]for r in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())}
 words=bound_blob(raw,refs,syms);assert words[0]==0x27bdffc0
 report=dict(raw_words=388,retail_words=360,frame=64,neighbors_unchanged=32,pools_unchanged=True,source_installed=False,c_match_credit=0)
 (OUT/'source-report.json').write_text(json.dumps(report,indent=2)+'\n');check_inputs();return words
def adjusted(words):
 words=list(words)
 for row in PIN['schedule']:
  at=row['offset']//4;assert words[at]==int(row['expected'],16);words[at]=int(row['replacement'],16)
 return words
def ordered_proof():
 from tools.tests import game_strip_constructor_151acbd4_private_proof as p
 p.P=OUT
 raw=p.words('v35');code=adjusted(raw)
 opening=p.compare('v35',2);assert opening['paths']==opening['equal_paths']==4
 original=p.compare('v35',None);assert original['paths']==10 and original['equal_paths']==2
 assert all(row['part']==0 and row['detail'][0]==12 for row in original['failures'])
 full=p.compare('v35-four-word-private-schedule',None,code);assert full['paths']==full['equal_paths']==10
 controls=[]
 for label,old,new in [('return-value',0x00601025,0x00001025),('time-clear-field',0xe46c004c,0xe46c0050)]:
  bad=code[:];assert bad.count(old)==1,(label,hex(old));bad[bad.index(old)]=new
  result=p.compare(label,None,bad);assert result['equal_paths']<result['paths'],('ineffective control',label)
  controls.append(dict(label=label,paths=result['paths'],rejected_paths=result['paths']-result['equal_paths']))
 report=dict(opening=opening,raw_order_frontier=original,complete_relation=full,effective_controls=controls,
  complete_provider_return_relation_proved=True,private_schedule_words=4,production_guards_installed=0,
  fresh_disjoint_allocator_objects=True,all_80_private_incoming_home_bytes=True,ordered_FP_FCSR_compared=True,
  full_fault_register_relation_proved=False,overlapping_allocations_proved=False,full_callers_qualified=False,
  source_installed=False,c_match_credit=0)
 (OUT/'ordered-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
