"""Oriented motion guarded C, owner and literal image audit."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_15115E0C','generated_142560'
ENTRY,ROM,BODY,SIZE=0x15115E0C,0x1432BC,208,208
SOURCE='conker/src/game/generated_142560.c'
OBJECT='conker/build/src/game/generated_142560.c.o'
ASM='conker/asm/142560.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-oriented-motion-pair-15115E0C-match'
RAW_SHA='124c83d97fe61c59cfe9fa5160345a8f9deeb50aeafdc766cf31703d4a6ab469'
TRUTH_SHA='0feb5d9a507961f4b6a5ec28b18a1306bc3d61eed625a8bfc3d1d779cc5097e8'
BEFORE_ELF_SHA='28aa241d6bd4b4d4edf654f0435d4762c39e2386be4e2f23c6bcb69a5ee7d80b'
BINDINGS={12:[('R_MIPS_HI16','D_800A2FA0')],16:[('R_MIPS_LO16','D_800A2FA0')],32:[('R_MIPS_26','func_150AD780')],44:[('R_MIPS_HI16','D_800A2FA4')],48:[('R_MIPS_LO16','D_800A2FA4')],64:[('R_MIPS_26','func_150AD78C')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
NEW_GUARDS=[]
HEADERS='#include <ultra64.h>\nextern f32 D_800A2FA0, D_800A2FA4;\nf32 func_150AD780(f32);\nf32 func_150AD78C(f32);\n'
SELECTED='/* Apply the oriented target displacement when state flag 4 is set. */\nvoid func_15115E0C(u8 *state, u8 *target) {\n    f32 cosine;\n    f32 sine;\n    f32 deltaX;\n    f32 deltaZ;\n\n    cosine = func_150AD780(*(f32 *)(state + 4) * D_800A2FA0);\n    sine = func_150AD78C(*(f32 *)(state + 4) * D_800A2FA4);\n    deltaX = *(f32 *)(target + 0x14) - (f32)*(s16 *)(state + 0x10);\n    deltaZ = *(f32 *)(target + 0x1C) - (f32)*(s16 *)(state + 0x14);\n    if ((state[0x4F] & 4) == 4) {\n        *(f32 *)(state + 0x7C) += sine * deltaX + cosine * deltaZ;\n        *(f32 *)(state + 0x80) -= sine * deltaZ + cosine * deltaX;\n    }\n}\n'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Oriented motion payload/bindings changed')
 return raw,bindings
CALLER='func_15115EDC'
CALLER_ENTRY,CALLER_ROM,CALLER_BODY=0x15115EDC,0x14338C,140
CALLER_RAW_SHA='d0e0ef8f20ed02ba53f824a457b8729b8e91586854eed06634b2780f47be47a3'
CALLER_BINDINGS={32:[('R_MIPS_26',FUNCTION)]}
CALLER_SELECTED='void func_15115EDC(u8 *arg0, u8 *arg1) {\n    f32 old_x;\n    f32 old_z;\n    f32 x;\n    f32 z;\n\n    old_x = *(f32 *) (arg0 + 0x7C);\n    old_z = *(f32 *) (arg0 + 0x80);\n    func_15115E0C(arg0, arg1);\n\n    if (*(u16 *) (arg1 + 0x84) == 0x4B) {\n        x = *(f32 *) (arg0 + 0x7C);\n        z = *(f32 *) (arg0 + 0x80);\n        old_x = (x - old_x) * 4.0f;\n        old_z = (z - old_z) * 4.0f;\n        *(f32 *) (arg0 + 0x7C) = x + old_x;\n        *(f32 *) (arg0 + 0x80) = z + old_z;\n    }\n}\n'
LEGACY_GUARD=b'generated_142560,func_15115EDC,0x018,0x8FA60024,0x8FA50024,-,-,Preserve cross-declaration record-pointer register,,,false'

def checked_caller_payload(raw,bindings):
 if len(raw)!=CALLER_BODY or sha(raw)!=CALLER_RAW_SHA or bindings!=CALLER_BINDINGS:raise ValueError('Motion caller payload/bindings changed')
 return raw,bindings

def recovered_owner(before):
 old='s32 func_15115E0C(f32 arg0, f32 arg1, u8 *arg2) {\n    return 0;\n}'
 call='func_15115E0C(old_x, old_z, arg1);'
 if before.count(old)!=1 or before.count(call)!=1:raise ValueError('Motion pair old ABI changed')
 declarations='\n'.join(HEADERS.splitlines()[1:])+'\n\n'
 return before.replace(old,declarations+SELECTED.rstrip(),1).replace(call,'func_15115E0C(arg0, arg1);',1)

def proposed_guards(before):
 rows=before.splitlines(keepends=True);target=[row for row in rows if row.startswith(b'generated_142560,func_15115EDC,')]
 if len(target)!=1 or target[0].rstrip(b'\r\n')!=LEGACY_GUARD:raise ValueError('Motion caller legacy ABI guard changed')
 return b''.join(row for row in rows if row!=target[0])

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
 if a!=b:raise ValueError(('Motion owner diagnostics changed',a-b,b-a))
 return dict(before=sum(a.values()),after=sum(b.values()),removed=0)

def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Oriented motion predictor baseline changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,24):raise ValueError('Oriented motion predecessor extent changed')
 struct.pack_into('>I',result,rows[0][0]+8,BODY)
 # New undefined references rotate three closed GNU ld name/definition groups.
 # Reconstruct every byte from the pinned BEFORE image, preserving definitions.
 named={name:(pos,fields,stringpos) for pos,name,fields,stringpos in symbol_rows(before)}
 groups=((('D_800991C0','D_8009E6D0'),(1,0)),
         (('D_800A2FA4','D_800907A4'),(1,0)),
         (('D_800A2FA0','D_8008F8C4','D_800D35E4'),(1,2,0)))
 for names,order in groups:
  slots=[named[name] for name in names];start=slots[0][2];base=slots[0][1][0];cursor=0
  for i,(name,(pos,fields,location)) in enumerate(zip(names,slots)):
   if (pos-slots[0][0],fields[0]-base,location-start)!=(16*i,cursor,cursor):raise ValueError('Motion closed metadata group moved')
   cursor+=len(name)+1
  labels=b''.join(name.encode()+b'\0' for name in names)
  if before[start:start+cursor]!=labels:raise ValueError('Motion metadata names changed')
  if any(start<=loc<start+cursor and name not in names for _,name,_,loc in symbol_rows(before)):raise ValueError('Motion substring reference changed')
  result[start:start+cursor]=b''.join(names[j].encode()+b'\0' for j in order);cursor=0
  for slot,j in zip(slots,order):
   struct.pack_into('>IIIBBH',result,slot[0],base+cursor,*slots[j][1][1:]);cursor+=len(names[j])+1
 return bytes(result)

SNAPSHOT_SHA='22041163247dde107def7ac630209469a9632129f5c16ede0cdc16a6ead5e76d'
PREPARED_SHA='9867293b8807e0d853131a9765d86113c79158feaa16d14694ca300338880dcc'
NEIGHBORS=82
EVIDENCE=('selected-final.o', 'selected-final.c', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_15115E0C.o', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner-diagnostics.txt', 'proposed-owner.c', 'qualified-padded.o', 'qualified-padded.s', 'before-padded.o', 'Make-commands.json', 'actual-Make-plan.txt', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_142560.c.o', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification.json', 'caller-census.json', 'proposed-guards.csv','original-func_15115EDC.o','legacy-guard-proof.json')

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Oriented motion input index changed')
 values={}
 for name,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+name.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Oriented motion frozen input changed: '+name)
  values[name]=value
 return values
def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Oriented motion preparation index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Oriented motion evidence set changed')
 for name,h in rows.items():
  if sha((output/name).read_bytes())!=h:raise ValueError('Oriented motion prepared artifact changed: '+name)
 q=json.loads((output/'preparation.json').read_text())
 if not(q['complete']and q['strict_whole_image_prediction']and q['actual_Make_object_equals_qualified']and q['neighbors']==NEIGHBORS and q['guards']==0 and q['exclusions']==0):raise ValueError('Oriented motion preparation failed')
 return rows
def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Oriented motion literal whole-image mismatch')
 expected=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if expected!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Oriented motion named definitions changed')
def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:
  changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/retail_word_patches.us.csv':proposed_guards(values['conker/retail_word_patches.us.csv'])}
  changes['conker/build/conker.us.elf']=predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Oriented motion live input changed: '+name)
 return values
def audit(root,output):
 from tools.match_progress import load_elf_functions
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or[name for name in a if a[name]!=b[name]]!=[FUNCTION]:raise ValueError('Oriented motion linked neighbor/address changed')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Oriented motion protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=52,frame=32,alignment_words=0,guards=0,direct_C_match=True,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result
