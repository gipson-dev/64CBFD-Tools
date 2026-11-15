"""Private complete three-vertex renderer recovery; never awards match credit."""
from pathlib import Path
import hashlib,json,os,struct,sys
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
OUT=ROOT/'conker/build/game-side-ring-renderer-1519fe6c-private'
SOURCE='conker/src/game/generated_1CC440.c';NAME='func_1519FE6C'
ENTRY,ROM,SIZE=0x1519FE6C,0x1CD31C,2528
PIN=json.loads(Path(__file__).with_name('game_side_ring_renderer_1519fe6c_manifest.json').read_text())

def immutable():
 record=json.loads((OUT/'production-baseline/fingerprints.json').read_text())
 for n,h in record['inputs'].items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h,n
 return len(record['inputs'])

def recover(before,pin=None):
 pin=PIN if pin is None else pin;stub='s32 func_1519FE6C() {\n    return 0;\n}'
 assert before.count(stub)==before.count('extern s32 D_800BE9E4;')==1
 return before.replace('extern s32 D_800BE9E4;',pin['declarations']+'\nextern s32 D_800BE9E4;',1).replace(stub,pin['source'])

def storage(obj):
 sys.path.insert(0,str(ROOT/'tools/ultralib/tools'));from libelf import ElfFile
 from mdebug import EcoffSt
 for fdr in ElfFile(obj.read_bytes()).find_section_by_name('.mdebug').fdrs:
  for pdr in fdr.pdrs:
   if pdr.name==NAME:
    homes={x.name:x.value-0x100000000 if x.value&0x80000000 else x.value for x in pdr.symrs if x.st==EcoffSt.LOCAL}
    assert pdr.frameoffset==240 and {n:homes[n] for n in ('cursor','sync','texture','previousPosition','position')}==dict(cursor=-4,sync=-95,texture=-92,previousPosition=-36,position=-24)
    return homes
 raise AssertionError('Missing renderer ECOFF local-storage evidence')

def main():
 count=immutable();before=(OUT/'production-baseline'/SOURCE).read_text();assert (ROOT/SOURCE).read_text()==before
 baseline,bd=compile_owner(ROOT,OUT,before,'baseline');obj,ad=compile_owner(ROOT,OUT,recover(before),'qualified');assert bd==ad=='',bd+ad
 previous,pd=compile_owner(ROOT,OUT,recover(before,PIN['previous']),'previous');assert pd=='',pd
 prior,prior_d=compile_owner(ROOT,OUT,recover(before,PIN['prior_selected']),'prior-selected');assert prior_d=='',prior_d
 for pin,path in ((PIN,obj),(PIN['previous'],previous),(PIN['prior_selected'],prior)):
  raw,refs=payload(path,NAME);assert hashlib.sha256(raw).hexdigest()==pin['raw_sha256']
  assert {str(k):v for k,v in refs.items()}=={k:[tuple(x) for x in v] for k,v in pin['refs'].items()}
  assert same_functions(baseline,path,(NAME,))==38
  assert sections(path)['.rodata'][1]==bytes.fromhex('38d1b717469c4000c614700038d1b717')
  assert normalized_pools(baseline)['.data']==normalized_pools(path)['.data']
 assert sections(baseline)['.rodata'][1]==bytes.fromhex('38d1b717469c4000c614700000000000')
 homes=storage(obj);raw,refs=payload(obj,NAME);assert len(raw)==637*4
 from tools.tests import game_side_ring_renderer_1519fe6c_oracle as g
 p=g.programs();differences=sum(a!=b for a,b in zip(p['candidate'],p['retail']))+5
 report=dict(frozen_inputs=count,raw_words=637,retail_words=632,raw_frame=240,retail_frame=240,neighbors=38,raw_sha256=PIN['raw_sha256'],bindings=len(refs),word_differences=differences,private_exposed_homes=dict(cursor=-4,sync=-95),IDO_local_storage=homes,previous_raw_words=648,previous_raw_frame=248,prior_selected_words=639,prior_selected_frame=232,only_compact_alignment_word_replaced_by_target_literal=True,opening_and_fade_proof='separate instruction-driven test',normalization_proved=False,production_unchanged=True,source_installed=False,c_match_credit=0)
 (OUT/'proposed-owner.c').write_text(recover(before));(OUT/'recovery-report.json').write_text(json.dumps(report,indent=2)+'\n');assert immutable()==count
 print(json.dumps({k:v for k,v in report.items() if k!='IDO_local_storage'}),flush=True)
if __name__=='__main__':main()
