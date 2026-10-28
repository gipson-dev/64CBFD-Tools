"""Actor point effects: isolated typed C, actual Make and strict whole-image qualification."""
from pathlib import Path
import hashlib,json,re,struct,sys
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
from tools.pad_generated_object import parse_object
import tools
sys.path.insert(0,tools.__path__[0])
from tools.pad_c_object import emit_padded_assembly
FUNCTION,OWNER='func_15138BC0','game_161520'
ENTRY,ROM,BODY,SIZE=0x15138BC0,0x166070,192,192
SOURCE='conker/src/game_161520.c'
OBJECT='conker/build/src/game_161520.c.o'
TU='conker/src/game/translation_units/161520_actor_point_effects.c'
ASM='conker/asm/nonmatchings/game_161520/func_15138BC0.s'
BUILD='conker/build/game-actor-point-effects-match'
RAW_SHA='8efc0e2faf71469d4b0bbb0ddcb3d5e2c0637f7ce508305676fe9a2fa64ef36d'
SNAPSHOT_SHA='24f596062d697805f39c3c110fd08b8f48db6e8fe4dd623d286fd53a5d6b9a59'
BEFORE_ELF_SHA='3c81e36f7918af9b6d8b869107e1cad4dd6de9b4bfa25ba5d3af2dcb9faea977'
TRUTH_SHA='6ffe7b23057f93cec1e949c26947798594c578436adcc6f5e265bc85cb70f088'
BINDINGS={28:[('R_MIPS_26','func_15134070')],56:[('R_MIPS_26','func_151380B4')],76:[('R_MIPS_26','func_15138120')],100:[('R_MIPS_26','func_1504715C')],128:[('R_MIPS_26','func_151382E0')],164:[('R_MIPS_26','func_15138424')]}
HEADERS="#include <ultra64.h>\n#include \"structs.h\"\n\ntypedef struct ActorEffectSurface {\n    f32 height;\n    s16 vertices[9];\n    s16 pad16;\n    u32 metadata;\n    u8 flags;\n    u8 state;\n    u16 pad1E;\n    s32 value;\n} ActorEffectSurface;\n\ns32 func_15134070(struct102 *);\ns32 func_151380B4(struct102 *, s32, vertex *);\ns32 func_15138120(struct102 *, s32, u8);\nvoid func_1504715C(ActorEffectSurface *, struct102 *);\ns32 func_151382E0(vertex *position, s32 type, ActorEffectSurface *surface, u8 group, s32 context);\ns32 func_15138424(struct102 *actor, vertex *position, s32 type, ActorEffectSurface *surface, u8 group, s32 context);\n\n"
SELECTED="/* Dispatch the selected actor effect, adding point-based effects when a point is available. */\nvoid func_15138BC0(struct102 *actor, u8 group, s32 context) {\n    s32 type;\n    vertex position;\n    u8 available;\n    ActorEffectSurface surface;\n\n    type = func_15134070(actor);\n    if (type != 99) {\n        available = func_151380B4(actor, type, &position);\n        func_15138120(actor, type, 1);\n        if (available) {\n            func_1504715C(&surface, actor);\n            func_151382E0(&position, type, &surface, group, context);\n            func_15138424(actor, &position, type, &surface, group, context);\n        }\n    }\n}\n"
sha=lambda b:hashlib.sha256(b).hexdigest()
def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Actor point effects body/bindings changed')
 return raw,bindings
def recovered_owner(before):
 declaration='s32 func_15138BC0();'
 stub='/* Non-matching C placeholders for asm/nonmatchings/game_161520/func_15138BC0.s. */\ns32 func_15138BC0() {\n    return 0;\n}'
 if before.count(declaration)!=1 or before.count(stub)!=1:raise ValueError('Actor point effects placeholder changed')
 return before.replace(declaration,'void func_15138BC0(struct102 *actor, u8 group, s32 context);').replace(stub,'\n\n/* Actor point effects are compiled in game/translation_units/161520_actor_point_effects.c. */\n')
def check_owner_diagnostics(text):
 normalized=re.sub(r'build/game-actor-point-effects-match/[^,:]+','OWNER',text)
 if normalized.count('Warning 712:')!=2 or normalized.count('illegal combination of pointer and integer')!=2 or re.search(r'Error|Warning (?!712)',normalized):raise ValueError('Actor point effects inherited diagnostics changed')
 return 2
def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Actor point effects snapshot changed')
 values={}
 for name,wanted in json.loads(data)['INPUTS'].items():
  b=(output/('before-'+name.replace('/','_'))).read_bytes()
  if sha(b)!=wanted:raise ValueError('Actor point effects frozen input changed: '+name)
  values[name]=b
 if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Actor point effects predecessor changed')
 return values
def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:
  changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/Makefile':(output/'proposed-Makefile').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
  if(root/TU).read_bytes()!=(HEADERS+SELECTED).encode():raise ValueError('Actor point effects installed TU changed')
 elif(root/TU).exists():raise ValueError('Actor point effects private TU installed early')
 for name,b in values.items():
  if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Actor point effects live input differs: '+name)
 return values
def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Actor point effects strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Actor point effects original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Actor point effects image differs from body and extent prediction')
    expected=Counter((n,f[1],192 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Actor point effects named ELF definitions changed')



ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','proposed-Makefile','selected-input.c','selected.o','original-'+FUNCTION+'.o','first-linked.elf')
EVIDENCE=tuple(n+s for n in('before-owner','after-owner','selected')for s in('.c','-processed.c','.o','-diagnostics.txt'))+('actual-Make-plan.txt','Make-commands.json','actual-Make-diagnostics.txt','make-shadow/src/game_161520.c.o','make-shadow/src/game_161520.c.o.padded.s')
def verify_prepared(output):
 result={}
 for manifest,names in(('artifact-fingerprint.json',ARTIFACTS),('canonical-prepared-fingerprint.json',EVIDENCE)):
  rows=json.loads((output/manifest).read_text())
  if set(rows)!=set(names):raise ValueError('Actor point effects artifact set changed')
  for name,wanted in rows.items():
   if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor point effects artifact changed: '+name)
  result.update(rows)
 if(output/'selected-input.c').read_text()!=HEADERS+SELECTED or(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Actor point effects selected source/diagnostics changed')
 for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
 if(output/'make-shadow/src/game_161520.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Actor point effects Make object differs')
 q=json.loads((output/'preparation.json').read_text())
 if not q['complete']or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Actor point effects preparation changed')
 return result
def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Actor point effects changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Actor point effects protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=48,frame=96,alignment_words=0,slot_words=48,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
