"""Selected actor health command: direct C, owner and literal image audit."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_150746F0','game_981E0'
ENTRY,ROM,BODY,SIZE=0x150746F0,0xA1BA0,244,244
SOURCE='conker/src/game_981E0.c'
OBJECT='conker/build/src/game_981E0.c.o'
ASM='conker/asm/nonmatchings/game_981E0/func_150746F0.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-selected-actor-health-150746F0-match'
RAW_SHA='976d934344a6e53b764db94ec3b1c9376705196d78868affe11b55d962e7bd65'
TRUTH_SHA='3f7de60c3d6a6030d3775464c049ed8e93e884dc859740e1ef858078174fe0cb'
BEFORE_ELF_SHA='de2f98e649839cc9c13431342b06e4bf64ac072b6e41617c775eb1afac243678'
BINDINGS={8: [('R_MIPS_HI16', 'D_800BE616')], 12: [('R_MIPS_LO16', 'D_800BE616')], 32: [('R_MIPS_HI16', 'D_800D154C')], 36: [('R_MIPS_LO16', 'D_800D154C')], 16: [('R_MIPS_HI16', 'D_800D154C')], 28: [('R_MIPS_LO16', 'D_800D154C')], 64: [('R_MIPS_HI16', 'D_800CC2D0')], 68: [('R_MIPS_LO16', 'D_800CC2D0')], 76: [('R_MIPS_HI16', 'D_800D1580')], 80: [('R_MIPS_LO16', 'D_800D1580')], 136: [('R_MIPS_26', 'func_1507CD64')], 220: [('R_MIPS_26', 'func_1517F488')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
NEW_GUARDS=[]
HEADERS='#include <ultra64.h>\n#include "structs.h"\nextern u8 D_800BE616;\nextern struct127 *D_800D154C;\nextern struct127 D_800CC2D0[26];\nextern s32 D_800D1580;\ns32 func_1507CD64(struct127 *, s32);\nvoid func_1517F488(s32,s32,s32,s32,s32,s32);\n'
SELECTED='/* Apply the command amount to the selected actor and submit its resulting effect. */\nvoid func_150746F0(void) {\n    struct127 *actor;\n\n    actor = NULL;\n    if (D_800BE616 != 0) {\n        actor = D_800D154C;\n    } else if (D_800D154C->unk13C != 0) {\n        actor = D_800CC2D0;\n    }\n    if (actor != NULL) {\n        if (actor->health <= D_800D1580) {\n            actor->health = 0;\n            D_800D154C->health = 0;\n            if (actor->interaction_state == 1) {\n                actor->immune = 0xFF;\n                func_1507CD64(actor, 6);\n            }\n        } else {\n            actor->health -= (u32)D_800D1580;\n            /* Effect state exposes an enable byte at offset 0x197. */\n            if ((actor->unk31C != NULL) && (actor->camera != NULL) && (((u8 *)actor->unk31C)[0x197] != 0)) {\n                func_1517F488(0xFF, 0, 0, 0xB4, 0x14, actor->camera->unk23D);\n            }\n        }\n    }\n}\n'
DECLARATIONS='s32 func_1507CD64(struct127 *, s32);\nvoid func_1517F488(s32,s32,s32,s32,s32,s32);\n'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Selected actor health payload/bindings changed')
 return raw,bindings
def recovered_owner(before):
 old='/* Non-matching C placeholders for asm/nonmatchings/game_981E0/func_150746F0.s. */\ns32 func_150746F0() {\n    return 0;\n}'
 if before.count(old)!=1 or before.count('s32 func_150746F0();')!=1:raise ValueError('Selected actor health placeholder changed')
 result=before.replace(old,SELECTED.rstrip(),1).replace('s32 func_150746F0();','void func_150746F0(void);',1)
 return result.replace('#include "variables.h"','#include "variables.h"\n\n'+DECLARATIONS,1)

def diagnostic_rows(text):
 rows=[]
 lines=text.splitlines()
 for i,line in enumerate(lines):
  match=re.match(r'cfe: Warning (\d+): .*?, line \d+: (.*)',line)
  if match:rows.append((match[1],match[2],lines[i+1].strip()))
  elif line.startswith('cfe:')and 'Warning'not in line:raise ValueError('Unexpected compiler diagnostic')
 return Counter(rows)
def check_owner_diagnostics(before,after):
 a,b=diagnostic_rows(before),diagnostic_rows(after)
 if a!=b:raise ValueError('Selected actor health owner diagnostics changed')
 return dict(before=sum(a.values()),after=sum(b.values()),removed=0)
def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Selected actor health predictor baseline changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Selected actor health predecessor extent changed')
 struct.pack_into('>I',result,rows[0][0]+8,BODY)
 return bytes(result)


SNAPSHOT_SHA='b044e900844a1fbd4357c8ab447d6a416692b368f23d5b2bf59dacb2d261ce7d'
PREPARED_SHA='dd9d9bfcdb286f31867d886decfbfab200abc85a70e30fdc26fa739e4a605a76'
NEIGHBORS=327
EVIDENCE=('selected-final.o', 'selected-final.c', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_150746F0.o', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner-diagnostics.txt', 'proposed-owner.c', 'qualified-padded.o', 'qualified-padded.s', 'before-padded.o', 'Make-commands.json', 'actual-Make-plan.txt', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_981E0.c.o', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification.json', 'caller-census.json')

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Selected actor health input index changed')
 values={}
 for name,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+name.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Selected actor health frozen input changed: '+name)
  values[name]=value
 return values
def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Selected actor health preparation index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Selected actor health evidence set changed')
 for name,h in rows.items():
  if sha((output/name).read_bytes())!=h:raise ValueError('Selected actor health prepared artifact changed: '+name)
 q=json.loads((output/'preparation.json').read_text())
 if not(q['complete']and q['strict_whole_image_prediction']and q['actual_Make_object_equals_qualified']and q['neighbors']==NEIGHBORS and q['guards']==q['exclusions']==0):raise ValueError('Selected actor health preparation failed')
 return rows
def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Selected actor health literal whole-image mismatch')
 expected=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if expected!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Selected actor health named definitions changed')
def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Selected actor health live input changed: '+name)
 return values
def audit(root,output):
 from tools.match_progress import load_elf_functions
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or[name for name in a if a[name]!=b[name]]!=[FUNCTION]:raise ValueError('Selected actor health linked neighbor/address changed')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Selected actor health protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=61,frame=32,alignment_words=0,guards=0,direct_C_match=True,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result
