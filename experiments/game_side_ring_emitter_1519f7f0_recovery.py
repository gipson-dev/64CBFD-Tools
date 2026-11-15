"""Private semantic emitter screen; no normalization, adoption or match credit."""
from pathlib import Path
import hashlib,json,os,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
OUT=ROOT/'conker/build/game-side-ring-emitter-1519f7f0-private'
SOURCE='conker/src/game/generated_1CC440.c'
NAME='func_1519F7F0'
ENTRY,ROM,SIZE=0x1519F7F0,0x1CCCA0,1660
PIN=json.loads(Path(__file__).with_name('game_side_ring_emitter_1519f7f0_manifest.json').read_text())
def immutable():
 saved=json.loads((OUT/'production-baseline/fingerprints.json').read_text())
 for name,want in saved['inputs'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==want,name
 return len(saved['inputs'])
def recover(before):
 stub='s32 func_1519F7F0() {\n    return 0;\n}'
 assert before.count(stub)==before.count('extern s32 D_800BE9E4;')==1
 return before.replace('extern s32 D_800BE9E4;',PIN['declarations']+'\nextern s32 D_800BE9E4;',1).replace(stub,PIN['source'])
def main():
 count=immutable();before=(OUT/'production-baseline'/SOURCE).read_text();assert (ROOT/SOURCE).read_text()==before
 baseline,bd=compile_owner(ROOT,OUT,before,'baseline');obj,ad=compile_owner(ROOT,OUT,recover(before),'qualified');assert bd==ad==''
 raw,refs=payload(obj,NAME)
 assert hashlib.sha256(raw).hexdigest()==PIN['raw_sha256']
 assert {str(k):[list(x) for x in v] for k,v in refs.items()}==PIN['refs']
 words=struct.unpack('>416I',raw);assert words[0]==0x27BDFEF0 and words[-1]==0x27BD0110
 neighbors=same_functions(baseline,obj,(NAME,));assert neighbors==38
 assert normalized_pools(baseline)==normalized_pools(obj)
 (OUT/'proposed-owner.c').write_text(recover(before));assert immutable()==count
 report=dict(frozen_inputs=count,raw_words=416,retail_words=415,raw_frame=272,retail_frame=280,neighbors=neighbors,
             unchanged_owner_pools=True,raw_sha256=PIN['raw_sha256'],bindings=len(refs),production_unchanged=True,
             transition_private_offsets=dict(raw=-48,retail=-44),query_private_offsets=dict(raw=-128,retail=-140),
             normalization_proved=False,source_installed=False,c_match_credit=0)
 (OUT/'recovery-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
