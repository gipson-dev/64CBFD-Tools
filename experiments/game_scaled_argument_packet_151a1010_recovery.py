"""Maintained private scaled-packet sources and owner/provenance gates.

This experiment compiles candidates only. No normalized stream, guards or source
installation is supplied. The ordered candidate still has the wrong frame.
"""
from pathlib import Path
import hashlib,json,os,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
OUT=ROOT/'conker/build/game-scaled-argument-packet-151a1010-private'
FROZEN=OUT/'production-baseline'
SOURCE='conker/src/game/generated_1CC440.c'
NAME='func_151A1010'
ENTRY,CALLEE,CONST,ROM=0x151A1010,0x151A11CC,0x800A8D28,0x1CE4C0
PIN=json.loads(Path(__file__).with_name('game_scaled_argument_packet_151a1010_manifest.json').read_text())
def check_inputs():
 record=json.loads((FROZEN/'fingerprints.json').read_text())
 for name,h in record['inputs'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
 assert (ROOT/SOURCE).read_bytes()==(FROZEN/SOURCE).read_bytes()
 return len(record['inputs'])
def compile_and_check():
 check_inputs();before=(FROZEN/SOURCE).read_text();stub='s32 func_151A1010() {\n    return 0;\n}';assert before.count(stub)==1
 baseline,diagnostics=compile_owner(ROOT,OUT,before,'baseline');assert not diagnostics;rows=[]
 for label,key in(('candidate','original_frame_source'),('inline-updateformal','ordered_source')):
  obj,diagnostics=compile_owner(ROOT,OUT,before.replace(stub,PIN['declarations']+PIN[key]),label);assert not diagnostics
  raw,refs=payload(obj,NAME);kind='original-frame'if label=='candidate'else'ordered';assert hashlib.sha256(raw).hexdigest()==PIN['raw_sha256'][kind]
  assert same_functions(baseline,obj,(NAME,))==38 and normalized_pools(baseline)==normalized_pools(obj)
  words=bound_blob(raw,refs,{'D_800A8D28':CONST,'func_151A11CC':CALLEE});truth=retail()
  rows.append(dict(source=kind,words=len(words),frame=(-words[0])&65535,positional_differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-111),neighbors_unchanged=38,pools_unchanged=True))
 check_inputs();report=dict(private_only=True,c_match_credit=0,candidates=rows,production_inputs_unchanged=check_inputs())
 (OUT/'maintained-source-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
def retail():return list(struct.unpack_from('>111I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM))
def programs():
 result={'retail':retail()}
 for label,obj in(('original-frame','candidate'),('ordered','inline-updateformal')):
  raw,refs=payload(OUT/(obj+'.o'),NAME);assert hashlib.sha256(raw).hexdigest()==PIN['raw_sha256'][label]
  result[label]=bound_blob(raw,refs,{'D_800A8D28':CONST,'func_151A11CC':CALLEE})
 return result
def caller_census():
 blob=(ROOT/'conker/conker.us.bin').read_bytes();entry=ENTRY;values={'aligned_pointer_literals':entry,'aligned_JALs':0x0c000000|((entry>>2)&0x3ffffff),'aligned_Js':0x08000000|((entry>>2)&0x3ffffff)}
 rows={name:[]for name in values}
 for at,(w,)in enumerate(struct.iter_unpack('>I',blob[:len(blob)&~3])):
  for name,v in values.items():
   if w==v:rows[name].append(hex(4*at))
 assert not any(rows.values()),rows
 (OUT/'maintained-caller-census.json').write_text(json.dumps(dict(**rows,scope='aligned literals and direct J/JAL words in the retail blob; computed runtime references are not disproved'),indent=2)+'\n');return rows
if __name__=='__main__':print(json.dumps(compile_and_check()),flush=True)
