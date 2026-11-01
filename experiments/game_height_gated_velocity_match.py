"""Height-gated velocity command: direct C, owner and literal image audit."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_1506BCC8','game_981E0'
ENTRY,ROM,BODY,SIZE=0x1506BCC8,0x99178,288,288
SOURCE='conker/src/game_981E0.c'
OBJECT='conker/build/src/game_981E0.c.o'
ASM='conker/asm/nonmatchings/game_981E0/func_1506BCC8.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-height-gated-velocity-1506BCC8-match'
RAW_SHA='7ac56b788c854481e4c10b829530f2cc4fa4cc4fbcc4cbd02a507199bcadf9e0'
TRUTH_SHA='88a7921cbc4b73b7645b2e574fe0723a8e1ad7a025f26ea8c77bd41d0e0b9fe4'
BEFORE_ELF_SHA='45f1a369228dc3084cb6c601826e914a631d2c64f875b1ea00089c3e4d9b3829'
BINDINGS={4: [('R_MIPS_HI16', 'D_800D154C')], 8: [('R_MIPS_LO16', 'D_800D154C')], 60: [('R_MIPS_26', 'func_151EF610')], 76: [('R_MIPS_HI16', 'D_800D154C')], 80: [('R_MIPS_LO16', 'D_800D154C')], 68: [('R_MIPS_HI16', 'D_800D1580')], 72: [('R_MIPS_LO16', 'D_800D1580')], 232: [('R_MIPS_HI16', 'D_800D1580')], 252: [('R_MIPS_LO16', 'D_800D1580')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
NEW_GUARDS=[]
HEADERS='#include <ultra64.h>\n#include "structs.h"\nextern struct127 *D_800D154C;\nextern s32 D_800D1580;\ns32 func_151EF610(void);\n'
SELECTED='/* Apply vertical velocity at the reference height, with state-22 random scaling. */\nvoid func_1506BCC8(void) {\n    f32 heightDifference;\n\n    if (D_800D154C->interaction_state == 0x16) {\n        if (D_800D154C->y_position == D_800D154C->unk180) {\n            /* Add with retail 32-bit wrapping before the signed float conversion. */\n            D_800D154C->y_velocity = (f32)(s32)((u32)(func_151EF610() % 8) + (u32)D_800D1580);\n            if (D_800D154C->xz_velocity != 0.0f) {\n                D_800D154C->y_velocity *= D_800D154C->xz_velocity / 40.0f;\n            } else {\n                D_800D154C->y_velocity = 0.0f;\n            }\n        }\n    } else {\n        heightDifference = D_800D154C->y_position - D_800D154C->unk180;\n        if ((-5.0f < heightDifference) && (heightDifference < 5.0f)) {\n            D_800D154C->y_velocity = (f32)D_800D1580;\n        }\n    }\n}\n'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Height-gated velocity payload/bindings changed')
 return raw,bindings
def recovered_owner(before):
 old='// ???\n/* Non-matching C placeholders for asm/nonmatchings/game_981E0/func_1506BCC8.s. */\ns32 func_1506BCC8() {\n    return 0;\n}'
 if before.count(old)!=1 or before.count('s32 func_1506BCC8();')!=1:raise ValueError('Height-gated velocity placeholder changed')
 result=before.replace(old,SELECTED.rstrip(),1).replace('s32 func_1506BCC8();','void func_1506BCC8(void);',1)
 return result.replace('#include "variables.h"','#include "variables.h"\n\ns32 func_151EF610(void);',1)

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
 if a!=b:raise ValueError('Height-gated velocity owner diagnostics changed')
 return dict(before=sum(a.values()),after=sum(b.values()),removed=0)
def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Height-gated velocity predictor baseline changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Height-gated velocity predecessor extent changed')
 struct.pack_into('>I',result,rows[0][0]+8,BODY)
 return bytes(result)


SNAPSHOT_SHA='eaf34c0a879a725d90e6349cfd10dc64b1d40c0c7cbfa030b84f6ebce3296937'
PREPARED_SHA='f27f4a91da9c5aa683bc11bbabb99726ca6c2f441ea38d6bcc526e20223bb59b'
NEIGHBORS=327
EVIDENCE=('selected-final.o', 'selected-final.c', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_1506BCC8.o', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner-diagnostics.txt', 'proposed-owner.c', 'qualified-padded.o', 'qualified-padded.s', 'before-padded.o', 'Make-commands.json', 'actual-Make-plan.txt', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_981E0.c.o', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification.json', 'caller-census.json', 'cached-actor-negative.o')

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Height-gated velocity input index changed')
 values={}
 for name,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+name.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Height-gated velocity frozen input changed: '+name)
  values[name]=value
 return values
def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Height-gated velocity preparation index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Height-gated velocity evidence set changed')
 for name,h in rows.items():
  if sha((output/name).read_bytes())!=h:raise ValueError('Height-gated velocity prepared artifact changed: '+name)
 q=json.loads((output/'preparation.json').read_text())
 if not(q['complete']and q['strict_whole_image_prediction']and q['actual_Make_object_equals_qualified']and q['neighbors']==NEIGHBORS and q['guards']==q['exclusions']==0):raise ValueError('Height-gated velocity preparation failed')
 return rows
def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Height-gated velocity literal whole-image mismatch')
 expected=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if expected!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Height-gated velocity named definitions changed')
def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Height-gated velocity live input changed: '+name)
 return values
def audit(root,output):
 from tools.match_progress import load_elf_functions
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or[name for name in a if a[name]!=b[name]]!=[FUNCTION]:raise ValueError('Height-gated velocity linked neighbor/address changed')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Height-gated velocity protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=72,frame=24,alignment_words=0,guards=0,direct_C_match=True,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result
