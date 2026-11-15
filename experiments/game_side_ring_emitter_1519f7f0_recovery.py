"""Private semantic emitter screen; no normalization, adoption or match credit."""
from pathlib import Path
import hashlib,json,os,struct,sys
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
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
def local_storage(obj):
 sys.path.insert(0,str(ROOT/'tools/ultralib/tools'))
 from libelf import ElfFile
 from mdebug import EcoffSt
 for fdr in ElfFile(obj.read_bytes()).find_section_by_name('.mdebug').fdrs:
  for pdr in fdr.pdrs:
   if pdr.name==NAME:
    values={x.name:x.value-0x100000000 if x.value&0x80000000 else x.value for x in pdr.symrs if x.st==EcoffSt.LOCAL}
    assert pdr.frameoffset==280 and {n:values[n] for n in ('inverseLength','transition','position','velocity','point')}==dict(inverseLength=-36,transition=-44,position=-80,velocity=-112,point=-140)
    return values
 raise AssertionError('Missing emitter ECOFF local-storage evidence')
def main():
 count=immutable();before=(OUT/'production-baseline'/SOURCE).read_text();assert (ROOT/SOURCE).read_text()==before
 baseline,bd=compile_owner(ROOT,OUT,before,'baseline');obj,ad=compile_owner(ROOT,OUT,recover(before),'qualified');assert bd==ad==''
 previous=PIN['previous'];old=before.replace('extern s32 D_800BE9E4;',previous['declarations']+'\nextern s32 D_800BE9E4;',1).replace('s32 func_1519F7F0() {\n    return 0;\n}',previous['source'])
 old_obj,od=compile_owner(ROOT,OUT,old,'previous');assert od==''
 old_raw,old_refs=payload(old_obj,NAME);assert hashlib.sha256(old_raw).hexdigest()==previous['raw_sha256']
 assert {str(k):[list(x) for x in v] for k,v in old_refs.items()}==previous['refs']
 raw,refs=payload(obj,NAME)
 assert hashlib.sha256(raw).hexdigest()==PIN['raw_sha256']
 assert {str(k):[list(x) for x in v] for k,v in refs.items()}==PIN['refs']
 words=struct.unpack('>415I',raw);assert words[0]==0x27BDFEE8 and words[-1]==0x27BD0118
 neighbors=same_functions(baseline,obj,(NAME,));assert neighbors==38
 assert normalized_pools(baseline)==normalized_pools(obj)
 assert same_functions(baseline,old_obj,(NAME,))==38 and normalized_pools(baseline)==normalized_pools(old_obj)
 storage=local_storage(obj)
 syms={x[1]:x[2][1] for x in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())}
 retail=struct.unpack_from('>415I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM)
 differences=sum(a!=b for a,b in zip(bound_blob(raw,refs,syms),retail));assert differences==240
 (OUT/'proposed-owner.c').write_text(recover(before));assert immutable()==count
 report=dict(frozen_inputs=count,raw_words=415,retail_words=415,raw_frame=280,retail_frame=280,neighbors=neighbors,
             unchanged_owner_pools=True,raw_sha256=PIN['raw_sha256'],bindings=len(refs),production_unchanged=True,
             transition_private_offsets=dict(raw=-44,retail=-44),query_private_offsets=dict(raw=-140,retail=-140),
             previous_raw_words=416,previous_raw_frame=272,semantic_local_storage_only=True,
             IDO_debug_local_storage=storage,
             real_word_differences=differences,
             normalization_proved=False,source_installed=False,c_match_credit=0)
 (OUT/'recovery-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
