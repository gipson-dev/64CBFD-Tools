"""Actor transformed/world-position query: direct C, owner and literal image audit."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_1507E1D0','game_A9D90'
ENTRY,ROM,BODY,SIZE=0x1507E1D0,0xAB680,212,224
SOURCE='conker/src/game_A9D90.c'
OBJECT='conker/build/src/game_A9D90.c.o'
ASM='conker/asm/nonmatchings/game_A9D90/func_1507E1D0.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-actor-transform-position-1507E1D0-match'
RAW_SHA='8909bfb4b897b226be9f6b0a537a5c7cb4db94424ca4d81b934f4bd5dd68adf5'
TRUTH_SHA='32b278c5327393ee356ce39be26426f8ca9cbfca664c7a1cfe50c97b839653e4'
BEFORE_ELF_SHA='cded33da308db122019a82f17a72c6f77a3cda2274826ce9b593850acf7315d6'
BINDINGS={116: [('R_MIPS_26', 'func_15143134')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
NEW_GUARDS=[]
HEADERS='#include <ultra64.h>\n#include "functions.h"\n#include "variables.h"\nvoid func_15143134(f32 *, f32 *, u8 *);\n'
SELECTED="/* Query the actor's transformed vertical offset, or its live world position. */\nvoid func_1507E1D0(struct127 *actor, f32 *x, f32 *y, f32 *z) {\n    u8 *matrix;\n\n    if (actor->unk1D4 != NULL) {\n        struct17 offset;\n        struct17 position;\n        offset.unk0 = 0.0f;\n        offset.unk4 = actor->y_scale * 30.0f;\n        offset.unk8 = 0.0f;\n        matrix = (u8 *)actor->unk1D4;\n        if (actor->interaction_state == 1) {\n            matrix += 0x300;\n        } else if (actor->interaction_state == 30) {\n            matrix += 0xC0;\n        }\n        func_15143134((f32 *)&offset, (f32 *)&position, matrix);\n        *x = position.unk0;\n        *y = position.unk4;\n        *z = position.unk8;\n    } else {\n        *x = actor->x_position;\n        *y = actor->y_position;\n        *z = actor->z_position;\n    }\n}\n"

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Actor transformed position payload/bindings changed')
 return raw,bindings
OLD_BODY='s32 func_1507E1D0() {\n    return 0;\n}'
def recovered_owner(before):
 if before.count(OLD_BODY)!=1:raise ValueError("Actor transformed-position source baseline changed")
 result=before.replace(OLD_BODY,SELECTED.rstrip(),1)
 result=result.replace('s32 func_1507E1D0();\n','',1)
 result=result.replace('/* Non-matching C placeholders for asm/nonmatchings/game_A9D90/func_1507E1D0.s. */\n','',1)
 return result.replace('#include "variables.h"\n','#include "variables.h"\n\nvoid func_15143134(f32 *, f32 *, u8 *);\n',1)


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
 if a!=b:raise ValueError('Actor transformed position owner diagnostics changed')
 return dict(before=sum(a.values()),after=sum(b.values()),removed=0)
def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Actor transformed position predictor baseline changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Actor transformed position predecessor extent changed')
 struct.pack_into('>I',result,rows[0][0]+8,BODY)
 return bytes(result)


SNAPSHOT_SHA='cd813630bc61db8607d02b719c46c7a81a540f04e0985eef12c18925444335ec'
PREPARED_SHA='523ec5023d63f5d12234f58cf7dcab4453a9205da5f7e68cdfc594582f53bd15'
NEIGHBORS=15
EVIDENCE=('selected-final.o', 'selected-final.c', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_1507E1D0.o', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner-diagnostics.txt', 'proposed-owner.c', 'qualified-padded.o', 'qualified-padded.s', 'before-padded.o', 'Make-commands.json', 'actual-Make-plan.txt', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_A9D90.c.o', 'first-link.ld', 'first-linked.elf', 'first-linked.map', 'predicted-production.map', 'preparation.json', 'runtime-qualification.json', 'caller-census.json', 'caller-runtime.json', 'native-runtime.json')

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Actor transformed position input index changed')
 values={}
 for name,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+name.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Actor transformed position frozen input changed: '+name)
  values[name]=value
 return values
def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Actor transformed position preparation index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Actor transformed position evidence set changed')
 for name,h in rows.items():
  if sha((output/name).read_bytes())!=h:raise ValueError('Actor transformed position prepared artifact changed: '+name)
 q=json.loads((output/'preparation.json').read_text())
 if not(q['complete']and q['strict_whole_image_prediction']and q['actual_Make_object_equals_qualified']and q['neighbors']==NEIGHBORS and q['guards']==q['exclusions']==0):raise ValueError('Actor transformed position preparation failed')
 return rows
def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Actor transformed position literal whole-image mismatch')
 expected=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if expected!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Actor transformed position named definitions changed')
def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Actor transformed position live input changed: '+name)
 return values
def audit(root,output):
 from tools.match_progress import load_elf_functions
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or[name for name in a if a[name]!=b[name]]!=[FUNCTION]:raise ValueError('Actor transformed position linked neighbor/address changed')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Actor transformed position protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=53,frame=56,alignment_words=3,guards=0,direct_C_match=True,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result
