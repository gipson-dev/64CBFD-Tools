"""Path-node position command: direct C, owner and literal image audit."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_15077DBC','game_A28B0'
ENTRY,ROM,BODY,SIZE=0x15077DBC,0xA526C,224,224
SOURCE='conker/src/game_A28B0.c'
OBJECT='conker/build/src/game_A28B0.c.o'
ASM='conker/asm/nonmatchings/game_A28B0/func_15077DBC.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-path-node-position-15077DBC-match'
RAW_SHA='ab7ab595da2b0ed12ddbb1861a2511d81fa64cdde227156113596e27d9aa2921'
TRUTH_SHA='cb8fc822265cb60f762543609b9a6836e54c81cdafa81e7d1fc7a9e8211c15fd'
BEFORE_ELF_SHA='c3712c89cd6c08397b6cc14724a0514ac2264bb7ca8251d6dd2b8df3a7429552'
BINDINGS={0: [('R_MIPS_HI16', 'D_800D1890')], 4: [('R_MIPS_LO16', 'D_800D1890')], 12: [('R_MIPS_HI16', 'D_800D154C')], 20: [('R_MIPS_LO16', 'D_800D154C')], 32: [('R_MIPS_HI16', 'D_800D154C')], 36: [('R_MIPS_LO16', 'D_800D154C')], 44: [('R_MIPS_HI16', 'D_800D2104')], 48: [('R_MIPS_LO16', 'D_800D2104')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
NEW_GUARDS=[]
HEADERS='#include <ultra64.h>\n#include "functions.h"\n#include "variables.h"\ntypedef struct { s16 x; s16 pad2; s16 z; s16 pad6; } PathNode8;\n'
SELECTED='/* Copy the selected signed path-node coordinates using live actor/table loads. */\nvoid func_15077DBC(void) {\n    if (D_800D1890 != 0xFA) {\n        D_800D154C->unk21E = D_800D1890;\n    }\n    D_800D154C->x_position = ((PathNode8 **)D_800D2104)[D_800D154C->unk13F][D_800D154C->unk21E + 1].x;\n    D_800D154C->y_position = ((PathNode8 **)D_800D2104)[D_800D154C->unk13F][D_800D154C->unk21E + 1].pad2;\n    D_800D154C->z_position = ((PathNode8 **)D_800D2104)[D_800D154C->unk13F][D_800D154C->unk21E + 1].z;\n}\n'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Path-node position payload/bindings changed')
 return raw,bindings
OLD_BODY='void func_15077DBC(void) {\n    PathNode8 *temp_v0;\n\n    if (D_800D1890 != 0xFA) {\n        D_800D154C->unk21E = D_800D1890;\n    }\n\n    temp_v0 = &((PathNode8 **)D_800D2104)[D_800D154C->unk13F][D_800D154C->unk21E + 1];\n    D_800D154C->x_position = temp_v0->x;\n    D_800D154C->y_position = temp_v0->pad2;\n    D_800D154C->z_position = temp_v0->z;\n}'
def recovered_owner(before):
 if before.count(OLD_BODY)!=1:raise ValueError("Path-node source baseline changed")
 return before.replace(OLD_BODY,SELECTED.rstrip(),1)


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
 if a!=b:raise ValueError('Path-node position owner diagnostics changed')
 return dict(before=sum(a.values()),after=sum(b.values()),removed=0)
def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Path-node position predictor baseline changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,160):raise ValueError('Path-node position predecessor extent changed')
 struct.pack_into('>I',result,rows[0][0]+8,BODY)
 return bytes(result)


SNAPSHOT_SHA='352fea24109840a125b00b348c4cf83a716f958e8d375bd6fccb85d113b14e51'
PREPARED_SHA='2908e94a5939af4321c75281da88c423025ffcf2456503bd70d4eeacbbfd1767'
NEIGHBORS=210
EVIDENCE=('selected-final.o', 'selected-final.c', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_15077DBC.o', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner-diagnostics.txt', 'proposed-owner.c', 'qualified-padded.o', 'qualified-padded.s', 'before-padded.o', 'Make-commands.json', 'actual-Make-plan.txt', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_A28B0.c.o', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification.json', 'caller-census.json', 'raw-isolated-match.json', 'negative-cached-actor.o', 'negative-cached-table.o', 'negative-cached-node.o')

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Path-node position input index changed')
 values={}
 for name,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+name.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Path-node position frozen input changed: '+name)
  values[name]=value
 return values
def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Path-node position preparation index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Path-node position evidence set changed')
 for name,h in rows.items():
  if sha((output/name).read_bytes())!=h:raise ValueError('Path-node position prepared artifact changed: '+name)
 q=json.loads((output/'preparation.json').read_text())
 if not(q['complete']and q['strict_whole_image_prediction']and q['actual_Make_object_equals_qualified']and q['neighbors']==NEIGHBORS and q['guards']==q['exclusions']==0):raise ValueError('Path-node position preparation failed')
 return rows
def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Path-node position literal whole-image mismatch')
 expected=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if expected!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Path-node position named definitions changed')
def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Path-node position live input changed: '+name)
 return values
def audit(root,output):
 from tools.match_progress import load_elf_functions
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or[name for name in a if a[name]!=b[name]]!=[FUNCTION]:raise ValueError('Path-node position linked neighbor/address changed')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Path-node position protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=56,frame=0,alignment_words=0,guards=0,direct_C_match=True,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result
