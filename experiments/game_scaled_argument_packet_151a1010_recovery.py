"""Scaled-packet source, immutable inputs and complete owner provenance.

The recovered source keeps the retail frame and ordered FP sequence. Matching
normalization and all qualification remain separate, fail-closed gates.
"""
from pathlib import Path
import hashlib,json,os,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
OUT=ROOT/'conker/build/game-scaled-argument-packet-151a1010-private/frame-2491'
FROZEN=OUT.parent/'production-baseline'
SOURCE='conker/src/game/generated_1CC440.c'
NAME='func_151A1010'
ENTRY,CALLEE,CONST,ROM=0x151A1010,0x151A11CC,0x800A8D28,0x1CE4C0
PIN=json.loads(Path(__file__).with_name('game_scaled_argument_packet_151a1010_manifest.json').read_text())
def recover(before):
 stub='s32 func_151A1010() {\n    return 0;\n}';assert before.count(stub)==1
 return before.replace(stub,PIN['declarations']+PIN['fitted_source'])
def installed():
 before=(FROZEN/SOURCE).read_text();live=(ROOT/SOURCE).read_text();assert live in(before,recover(before));return live!=before
def check_inputs():
 record=json.loads((FROZEN/'fingerprints.json').read_text());active=installed();plan=json.loads((OUT/'adoption-plan.json').read_text())if active else{}
 if active:assert set(plan)=={SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game/generated_1CC440.c.o','conker/build/conker.us.elf'}
 for name,h in record['inputs'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==plan.get(name,h),name
 return len(record['inputs'])
def compile_and_check():
 check_inputs();before=(FROZEN/SOURCE).read_text()
 baseline,diagnostics=compile_owner(ROOT,OUT,before,'baseline');assert not diagnostics
 obj,diagnostics=compile_owner(ROOT,OUT,recover(before),'qualified');assert not diagnostics
 raw,refs=payload(obj,NAME);assert hashlib.sha256(raw).hexdigest()==PIN['raw_sha256']['fitted']
 assert same_functions(baseline,obj,(NAME,))==38 and normalized_pools(baseline)==normalized_pools(obj)
 words=bound_blob(raw,refs,{'D_800A8D28':CONST,'func_151A11CC':CALLEE});truth=retail()
 from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
 elf=(ROOT/'conker/build/conker.us.elf').read_bytes();assert struct.unpack_from('>I',elf,elf_slot_offset(elf,CONST,4))[0]==0x44bb8000
 report=dict(private_only=not installed(),c_match_credit=0,raw_words=len(words),frame=(-words[0])&65535,positional_differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-111),neighbors_unchanged=38,pools_unchanged=True,production_state_matches_audited_inputs=check_inputs())
 (OUT/'proposed-owner.c').write_text(recover(before));(OUT/'maintained-source-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
def retail():return list(struct.unpack_from('>111I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM))
def programs():
 from tools.experiments import game_scaled_argument_packet_151a1010_match as match
 raw,refs=payload(OUT/'qualified.o',NAME);normal,nrefs=match.normalize(raw,refs);symbols={'D_800A8D28':CONST,'func_151A11CC':CALLEE}
 return {'retail':retail(),'fitted':bound_blob(raw,refs,symbols),'guarded':bound_blob(normal,nrefs,symbols)}
def caller_census():
 blob=(ROOT/'conker/conker.us.bin').read_bytes();entry=ENTRY;values={'aligned_pointer_literals':entry,'aligned_JALs':0x0c000000|((entry>>2)&0x3ffffff),'aligned_Js':0x08000000|((entry>>2)&0x3ffffff)}
 rows={name:[]for name in values}
 for at,(w,)in enumerate(struct.iter_unpack('>I',blob[:len(blob)&~3])):
  for name,v in values.items():
   if w==v:rows[name].append(hex(4*at))
 assert not any(rows.values()),rows
 (OUT/'maintained-caller-census.json').write_text(json.dumps(dict(**rows,scope='aligned literals and direct J/JAL words in the retail blob; computed runtime references are not disproved'),indent=2)+'\n');return rows
if __name__=='__main__':print(json.dumps(compile_and_check()),flush=True)
