"""Motion/contact C drafts: original-frame screens without exact-match credit."""
from pathlib import Path
import hashlib,json,os,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
PACKET=ROOT/'conker/build/game-next-151b118c-private'
FROZEN=PACKET/'baseline'
OUT=Path(os.environ.get('CBFD_MOTION_IMPACT_WORK',PACKET/'adoption/qualification-primary')).resolve()
assert OUT.is_relative_to((ROOT/'conker/build').resolve())
PIN=json.loads(Path(__file__).with_name('game_motion_impact_151b118c_manifest.json').read_text())
NAME='func_151B118C';SOURCE=PIN['source'];STUB='s32 func_151B118C() {\n    return 0;\n}'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def check_inputs():
 assert sha(FROZEN/'fingerprints.json')==PIN['frozen_pin_sha256']
 pins=json.loads((FROZEN/'fingerprints.json').read_text())['inputs'];assert len(pins)==PIN['frozen_inputs']
 for n,h in pins.items():assert sha(ROOT/n)==h and sha(FROZEN/n)==h,n
 return len(pins)
def qualify_source():
 check_inputs();OUT.mkdir(exist_ok=False)
 before=(FROZEN/SOURCE).read_text();assert before.count(STUB)==1 and(ROOT/SOURCE).read_text()==before
 baseline,d=compile_owner(ROOT,OUT,before,'baseline');assert not d
 symbols={v[1]:v[2][1]for v in symbol_rows((FROZEN/'conker/build/conker.us.elf').read_bytes())}
 retail=(FROZEN/'conker/conker.us.bin').read_bytes()[0x1DE63C:0x1DE928];assert len(retail)==748
 truth=struct.unpack('>187I',retail);reports=[]
 for label,row in PIN['variants'].items():
  proposed=before.replace(STUB,PIN['declarations']+'\n'+row['body'])
  obj,d=compile_owner(ROOT,OUT,proposed,label);assert not d
  raw,refs=payload(obj,NAME);expected={int(k):[tuple(v)for v in values]for k,values in row['refs'].items()}
  assert len(raw)==row['words']*4 and hashlib.sha256(raw).hexdigest()==row['raw_sha256']and refs==expected
  words=bound_blob(raw,refs,symbols)
  assert words[0]==0x27BDFF68 and row['frame']==152
  diff=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-len(truth));assert diff==row['differences']
  assert same_functions(baseline,obj,(NAME,))==15 and normalized_pools(baseline)==normalized_pools(obj)
  (OUT/(label+'.body')).write_text(row['body']);(OUT/(label+'.decl')).write_text(PIN['declarations'])
  reports.append(dict(label=label,words=len(words),frame=152,differences=diff,neighbors_unchanged=15,pools_unchanged=True))
 (OUT/'retail.bin').write_bytes(retail)
 report=dict(passes=True,variants=reports,frozen_inputs=check_inputs(),source_installed=False,c_match_credit=0)
 (OUT/'source-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
