"""Private scalar smoother experiments; no production installation or matching credit."""
from pathlib import Path
import argparse,hashlib,json,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
FUNCTION='func_150495B0'
SOURCE='conker/src/game/generated_76A60.c'
ASM='conker/asm/76A60.s'
BUILD='conker/build/game-scalar-velocity-smoothing-150495B0-match'
ENTRY,ROM,RETAIL_WORDS=0x150495B0,0x76A60,54
RETAIL_SHA256='fd407656aa97f156766f9272be44befed09a21737c2595cc9edb107a19735a80'
SELECTED='#include <ultra64.h>\n\n/* Smooth one position and velocity toward a target, clamping overshoot. */\nvoid func_150495B0(f32 *position, f32 target, f32 *velocity, f32 strength,\n                   f32 damping, f32 deltaTime) {\n    f32 difference;\n    f32 direction;\n    f32 next;\n    f32 nextDirection;\n    difference = target - *position;\n    direction = difference < 0.0f ? -1.0f : 1.0f;\n    difference *= strength;\n    *velocity += (difference - *velocity) * damping * deltaTime;\n    next = *velocity * deltaTime + *position;\n    nextDirection = target < next ? -1.0f : 1.0f;\n    if (nextDirection == direction) {\n        *position = next;\n    } else {\n        *position = target;\n        *velocity = 0.0f;\n    }\n}\n'
sha=lambda data:hashlib.sha256(data).hexdigest()
def prepare(root,output):
 root=Path(root).resolve();output=Path(output).resolve()
 if not output.is_relative_to(root/'conker/build'):raise ValueError('Private output must stay inside the consumer build directory')
 output.mkdir(parents=True,exist_ok=True);before=(root/SOURCE).read_text();start,end=function_span(before,FUNCTION)
 if before[start:end]!='s32 func_150495B0() {\n    return 0;\n}':raise ValueError('Private smoother baseline is no longer the unconverted placeholder')
 truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+RETAIL_WORDS*4]
 if sha(truth)!=RETAIL_SHA256:raise ValueError('Smoother retail instructions changed')
 assembly=(root/ASM).read_text();assembly=assembly[assembly.index('glabel '+FUNCTION):assembly.index('endlabel '+FUNCTION)]
 original=output/('original-'+FUNCTION+'.s');original.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.text\n'+assembly+'.size '+FUNCTION+',.-'+FUNCTION+'\n')
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(original.with_suffix('.o')),str(original)],capture_output=True,check=True)
 retail,bindings=payload(original.with_suffix('.o'),FUNCTION)
 if retail!=truth or bindings:raise ValueError('Original smoother assembly or bindings differ from retail')
 obj,diag=compile_owner(root,output,SELECTED,'selected')
 if diag:raise ValueError(diag)
 raw,rs=payload(obj,FUNCTION);words=struct.unpack('>%dI'%(len(raw)//4),raw);tw=struct.unpack('>54I',retail)
 frame=next((-((w&65535)^32768)+32768 for w in words if w>>16==0x27BD),0)
 proposed=before[:start]+SELECTED[SELECTED.index('/* Smooth'):].rstrip()+before[end:]
 old,bd=compile_owner(root,output,before,'before-owner-screen');new,ad=compile_owner(root,output,proposed,'after-owner-screen')
 if bd or ad or payload(new,FUNCTION)!=(raw,rs) or normalized_pools(old)!=normalized_pools(new):raise ValueError('Private owner or pool qualification failed')
 neighbors=same_functions(old,new,(FUNCTION,))
 result=dict(private_only=True,installed=False,matching_credit=0,function=FUNCTION,normal_O2_g3=True,retail_words=54,candidate_words=len(words),retail_frame=24,candidate_frame=frame,real_word_differences=sum(a!=b for a,b in zip(words,tw))+abs(len(words)-54),bindings=len(rs),owner_neighbors=neighbors,owner_diagnostics_empty=True,pools_fixed=True,selected_SHA256=sha(SELECTED.encode()),retail_SHA256=sha(retail),candidate_SHA256=sha(raw),byte_matching_claimed=False)
 (output/'screen-qualification.json').write_text(json.dumps(result,indent=2)+'\n');return result

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--consumer-root',type=Path,default=Path(__file__).resolve().parents[2]);parser.add_argument('--output',type=Path);parser.add_argument('--qualify-semantics',action='store_true');args=parser.parse_args();root=args.consumer_root.resolve();output=args.output or root/BUILD
 report=prepare(root,output)
 if args.qualify_semantics:
  from tools.tests.game_scalar_velocity_smoothing_oracle import qualify
  report['semantics']=qualify(root,output)
  from tools.tests.game_scalar_velocity_smoothing_callers import qualify as qualify_callers
  report['callers']=qualify_callers(root,output)
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
