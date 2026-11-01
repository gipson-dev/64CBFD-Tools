"""Actor matrix position: direct C, local typed ABI, unchanged owner neighbors."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,struct
from tools.experiments.game_remaining_donor_candidates import function_span,compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_151644F4','game_18D770'
ENTRY,ROM,BODY,SIZE=0x151644F4,0x1919A4,208,208
SOURCE='conker/src/game_18D770.c'
OBJECT='conker/build/src/game_18D770.c.o'
ASM='conker/asm/nonmatchings/game_18D770/func_151644F4.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-actor-matrix-position-151644F4-match'
RAW_SHA='c5ebd93469dedf571311583e8c89177f6eea82cfafdff20083d261e60a2f2a21'
TRUTH_SHA='d4987d33ee5a4ffc1627621a8914b8785bfad1e88a53fb054fd08f3a71bd1150'
BEFORE_ELF_SHA='d3455d627d30e8555a2d7aca6c4132104a9090ba0f9753941aa2a8454de5ea1f'
BINDINGS={36:[('R_MIPS_26','func_150A8050')],112:[('R_MIPS_26','func_150A7960')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
NEW_GUARDS=[]
HEADERS='#include <ultra64.h>\n#include "structs.h"\n/* Private view of the state used by the vertical-point transform pair. */\ntypedef struct {\n    u8 retained[0x14];\n    struct226 *actor;\n    f32 height;\n    f32 angleScale;\n    struct17 *angleFactors;\n    struct17 translation;\n} ActorMatrixPositionState;\n\nvoid func_150A8050(f32 matrix[4][4], f32, f32, f32);\nvoid func_150A7960(f32 matrix[4][4], f32, f32, f32, f32 *, f32 *, f32 *);\n'
DECLARATIONS='/* Private view of the state used by the vertical-point transform pair. */\ntypedef struct {\n    u8 retained[0x14];\n    struct226 *actor;\n    f32 height;\n    f32 angleScale;\n    struct17 *angleFactors;\n    struct17 translation;\n} ActorMatrixPositionState;\n\nvoid func_150A8050(f32 matrix[4][4], f32, f32, f32);\nvoid func_150A7960(f32 matrix[4][4], f32, f32, f32, f32 *, f32 *, f32 *);\n\n\n'
SELECTED='/* Rotate and translate the vertical point, then publish actor coordinates.\n * Height and both angle arguments use the original o32 floating-value ABI. */\nvoid func_151644F4(ActorMatrixPositionState *owner, struct17 *translation, f32 height,\n                   f32 angleX, f32 angleZ) {\n    f32 point[3];\n    f32 matrix[4][4];\n    func_150A8050(matrix, angleX, 0.0f, angleZ);\n    matrix[3][0] = translation->unk0;\n    matrix[3][1] = translation->unk4;\n    matrix[3][2] = translation->unk8;\n    func_150A7960(matrix, 0.0f, height, 0.0f, &point[0], &point[1], &point[2]);\n    owner->actor->unkE = point[0];\n    owner->actor->unk10 = point[1];\n    owner->actor->unk12 = point[2];\n}\n'
PARENT='s32 func_151644A8(ActorMatrixPositionState *state) {\n    f32 angleScale;\n    struct17 *vector;\n\n    vector = state->angleFactors;\n    angleScale = state->angleScale;\n    func_151644F4(state, &state->translation, state->height,\n                  vector->unk0 * angleScale, vector->unk8 * angleScale);\n    return 1;\n}'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Actor matrix position payload/bindings changed')
 return raw,bindings
def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='void func_151644F4(struct242 *arg0, struct17 *arg1, s32 arg2, f32 arg3, f32 arg4) {\n}':raise ValueError('Actor transform placeholder changed')
 result=before[:a]+SELECTED.rstrip()+before[b:]
 result=result.replace('void func_151644F4(struct242 *arg0, struct17 *arg1, s32 arg2, f32 arg3, f32 arg4);','void func_151644F4(ActorMatrixPositionState *, struct17 *, f32, f32, f32);').replace('s32  func_151644A8(struct242 *arg0);','s32  func_151644A8(ActorMatrixPositionState *);')
 a,b=function_span(result,'func_151644A8');result=result[:a]+PARENT+result[b:]
 result=result.replace('#include "variables.h"','#include "variables.h"\n\n'+DECLARATIONS,1)
 result=result.replace('/* Non-matching C placeholders for asm/nonmatchings/game_18D770/func_151644F4.s. */\n','',1)
 a=result.index('// NON-MATCHING: close...',result.index('void func_151644F4(ActorMatrixPositionState *owner'));b=result.index('// loop\n',a);return result[:a]+result[b:]
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
 if b-a:raise ValueError('New actor owner diagnostics: '+repr(b-a))
 removed=a-b
 if any('func_151644F4('not in row[2]and'temp_v0 = arg0->unk20'not in row[2]for row in removed):raise ValueError('Unrelated diagnostics removed')
 return dict(before=sum(a.values()),after=sum(b.values()),removed=sum(removed.values()))
def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Actor transform predictor baseline changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,24):raise ValueError('Actor transform predecessor extent changed')
 struct.pack_into('>I',result,rows[0][0]+8,BODY)
 return bytes(result)

SNAPSHOT_SHA='b4212538da8314571d24a8c81d7e0649ea001545a44e632a703cb26c0ecc9608'
PREPARED_SHA='1881dd3e1bc209b8b04a920fbbe18ef656324070c08f7b5be9175d7704c80aaf'
EVIDENCE=('selected-final.o', 'selected-final.c', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_151644F4.o', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner-diagnostics.txt', 'proposed-owner.c', 'qualified-padded.o', 'qualified-padded.s', 'before-padded.o', 'Make-commands.json', 'actual-Make-plan.txt', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_18D770.c.o', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification.json')

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Actor transform input index changed')
 values={}
 for name,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+name.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Actor transform frozen input changed: '+name)
  values[name]=value
 return values
def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Actor transform preparation index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Actor transform evidence set changed')
 for name,h in rows.items():
  if sha((output/name).read_bytes())!=h:raise ValueError('Actor transform prepared artifact changed: '+name)
 q=json.loads((output/'preparation.json').read_text())
 if not(q['complete']and q['strict_whole_image_prediction']and q['actual_Make_object_equals_qualified']and q['neighbors']==77 and q['guards']==q['exclusions']==0):raise ValueError('Actor transform preparation failed')
 return rows
def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Actor transform literal whole-image mismatch')
 expected=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if expected!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Actor transform named definitions changed')
def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Actor transform live input changed: '+name)
 return values
def audit(root,output):
 from tools.match_progress import load_elf_functions
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or[name for name in a if a[name]!=b[name]]!=[FUNCTION]:raise ValueError('Actor transform linked neighbor/address changed')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Actor transform protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=52,frame=120,guards=0,direct_C_match=True,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result
