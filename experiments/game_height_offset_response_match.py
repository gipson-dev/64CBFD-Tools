"""Height offset response guarded C, owner and literal image audit."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_1511617C','generated_142560'
ENTRY,ROM,BODY,SIZE=0x1511617C,0x14362C,344,344
SOURCE='conker/src/game/generated_142560.c'
OBJECT='conker/build/src/game/generated_142560.c.o'
ASM='conker/asm/142560.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-height-offset-response-1511617C-match'
RAW_SHA='1acb45a8623cff04d963dc892a1c7a0d88c11764158857580ad7fe2a92a09f3a'
TRUTH_SHA='7670149c42e1e309575ce9130aaa9b06361c39846679b81406838cf9f40a24cc'
BEFORE_ELF_SHA='ef752d6de30fdb6cd6b23a51a476140e6fac2238a1686819edc572d4eb6f6664'
BINDINGS={52: [('R_MIPS_26', 'func_1510F648')], 144: [('R_MIPS_HI16', 'D_800A2FA8')], 148: [('R_MIPS_LO16', 'D_800A2FA8')], 80: [('R_MIPS_HI16', 'D_800CC354')], 196: [('R_MIPS_LO16', 'D_800CC354')], 224: [('R_MIPS_HI16', 'D_800A2FAC')], 228: [('R_MIPS_LO16', 'D_800A2FAC')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
HEADERS='#include <ultra64.h>\nextern u16 D_800CC354;\nextern f32 D_800A2FA8, D_800A2FAC;\nf32 func_1510F648(f32, f32, f32);\nf32 fabsf(f32);\n#pragma intrinsic (fabsf)\n'
SELECTED='/* Query the surface height, relax its signed offset, and retain the Y change. */\nvoid func_1511617C(u8 *state) {\n    s16 oldY = *(s16 *)(state + 0x12);\n    s32 velocity;\n    s32 target;\n\n    *(f32 *)(state + 0x7C) = func_1510F648((f32)*(s16 *)(state + 0x10),\n        (f32)*(s16 *)(state + 0x12), (f32)*(s16 *)(state + 0x14));\n    if (fabsf(*(f32 *)(state + 0x7C) - (f32)*(s16 *)(state + 0x12)) > 200.0f) {\n        *(s32 *)(state + 0x3C) = 0;\n    }\n    if (!(state[0x4F] & 4)) {\n        velocity = *(s32 *)(state + 0x3C);\n        *(s32 *)(state + 0x3C) = (s32)((f32)velocity +\n            (f32)(s32)(0u - (u32)velocity) * D_800A2FA8);\n    } else {\n        target = -20;\n        if (D_800CC354 == 0x4B) {\n            target = -40;\n        }\n        velocity = *(s32 *)(state + 0x3C);\n        *(s32 *)(state + 0x3C) = (s32)((f32)velocity +\n            (f32)(s32)((u32)target - (u32)velocity) * D_800A2FAC);\n    }\n    *(s16 *)(state + 0x12) = (s32)(*(f32 *)(state + 0x7C) + (f32)*(s32 *)(state + 0x3C));\n    *(s16 *)(state + 0x5C) = *(s16 *)(state + 0x12) - oldY;\n}\n'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Height offset response payload/bindings changed')
 return raw,bindings
def recovered_owner(before):
 old='s32 func_1511617C() {\n    return 0;\n}'
 if before.count(old)!=1:raise ValueError('Height response placeholder changed')
 declarations='\n'.join(HEADERS.splitlines()[1:])+'\n\n'
 return before.replace(old,declarations+SELECTED.rstrip(),1)


def normalized_payload(raw,bindings):
 checked_payload(raw,bindings);words=list(struct.unpack('>86I',raw));result=words[:]
 # Enlarge only the private frame. Incoming A0's saved home remains at entry SP.
 for at,expected,replacement in ((0,0x27BDFFE0,0x27BDFFD8),(36,0xAFA40020,0xAFA40028),(60,0x8FA40020,0x8FA40028),(340,0x27BD0020,0x27BD0028)):
  if words[at//4]!=expected:raise ValueError('Height private frame shape changed')
  result[at//4]=replacement
 # Reconstruct FP allocation from definitions and their live uses. The maps
 # are versioned at every definition, so reused FP registers cannot alias roles.
 blocks=((0x94,0xB8,{0x94:10,0x9C:4,0xA0:6,0xA4:0,0xA8:8,0xAC:16,0xB0:18,0xB4:4}),
         (0xE4,0x108,{0xE4:16,0xEC:6,0xF0:10,0xF4:0,0xF8:8,0xFC:18,0x100:4,0x104:6}),
         (0x118,0x130,{0x118:10,0x11C:16,0x124:8,0x128:18,0x12C:4}))
 for start,end,definitions in blocks:
  live={}
  for at in range(start,end+1,4):
   w=words[at//4];op=w>>26;rs=w>>21&31;rt=w>>16&31;fs=w>>11&31;fd=w>>6&31
   if op==0x31:
    dest=definitions[at];result[at//4]=(w&~0x001F0000)|(dest<<16);live[rt]=dest
   elif op==17 and rs==4:
    dest=definitions[at];result[at//4]=(w&~0x0000F800)|(dest<<11);live[fs]=dest
   elif op==17 and rs==0:
    if fs not in live:raise ValueError('Height MFC1 reads an unbound FP value')
    result[at//4]=(w&~0x0000F800)|(live[fs]<<11)
   elif op==17 and rs in(16,20):
    if fs not in live:raise ValueError('Height arithmetic reads an unbound FP value')
    left=live[fs];right=live[rt] if rs==16 and w&63 in(0,2)else rt
    if at==0x128:left,right=right,left
    dest=definitions[at];result[at//4]=(w&~0x001FFFC0)|(right<<16)|(left<<11)|(dest<<6);live[fd]=dest
   elif at in definitions:raise ValueError('Height FP definition instruction changed')
 answer=struct.pack('>86I',*result)
 if sha(answer)!=NORMALIZED_RAW_SHA:raise ValueError('Height closed transformation failed')
 return answer

def derive_guards(raw,bindings):
 normalized=normalized_payload(raw,bindings);rows=[(i,struct.unpack_from('>I',raw,i)[0],struct.unpack_from('>I',normalized,i)[0])for i in range(0,BODY,4)if raw[i:i+4]!=normalized[i:i+4]]
 if len(rows)!=27:raise ValueError('Height closed guard count changed')
 return rows

def proposed_guards(before):
 prefix=(OWNER+','+FUNCTION+',').encode()
 if any(v.startswith(prefix)for v in before.splitlines()):raise ValueError('Height guards already present')
 newline=b'\r\n'if b'\r\n'in before else b'\n'
 if not before.endswith(newline):raise ValueError('Height guard manifest newline changed')
 rows=[]
 for at,a,b in NEW_GUARDS:
  uses=BINDINGS.get(at,[]);binding=';'.join(k+':'+n for k,n in uses)or'-'
  rows.append(('%s,%s,0x%03X,0x%08X,0x%08X,%s,%s,Normalize height response closed private frame and FP allocation,,,false'%(OWNER,FUNCTION,at,a,b,binding,binding)).encode()+newline)
 return before+b''.join(rows)


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
 if a!=b:raise ValueError(('Angular velocity owner diagnostics changed',a-b,b-a))
 return dict(before=sum(a.values()),after=sum(b.values()),removed=0)

def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Height offset response predictor baseline changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Height offset response predecessor extent changed')
 struct.pack_into('>I',result,rows[0][0]+8,BODY)
 # Closed linker serialization groups introduced by the new coefficient uses.
 # Every name, definition and byte is reconstructed from the BEFORE image.
 named={n:(at,f,sp)for at,n,f,sp in symbol_rows(before)}
 groups=((('D_800A2FA8','D_800907A8','func_15112520'),(1,2,0)),(('D_800A2FAC','D_800907AC'),(1,0)))
 for names,order in groups:
  slots=[named[n]for n in names];start=slots[0][2];base=slots[0][1][0];cursor=0
  for i,(n,(at,f,sp))in enumerate(zip(names,slots)):
   if(at-slots[0][0],f[0]-base,sp-start)!=(16*i,cursor,cursor):raise ValueError('Height closed metadata group moved')
   cursor+=len(n)+1
  labels=b''.join(n.encode()+b'\0'for n in names)
  if before[start:start+cursor]!=labels:raise ValueError('Height metadata names changed')
  if any(start<=sp<start+cursor and n not in names for _,n,_,sp in symbol_rows(before)):raise ValueError('Height metadata substring reference changed')
  result[start:start+cursor]=b''.join(names[j].encode()+b'\0'for j in order);cursor=0
  for slot,j in zip(slots,order):struct.pack_into('>IIIBBH',result,slot[0],base+cursor,*slots[j][1][1:]);cursor+=len(names[j])+1
 return bytes(result)

SNAPSHOT_SHA='6075f3a8ac52b7cd95d2d9999a5bb64be7ef407074df6d93c0a0d77a37799536'
PREPARED_SHA='6971ab1b83b8b5993d33af5425d856850b0a3cbea8572b957ef3aa763d505e95'
NEIGHBORS=83
EVIDENCE=('selected-final.o', 'selected-final.c', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_1511617C.o', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner-diagnostics.txt', 'proposed-owner.c', 'qualified-padded.o', 'qualified-padded.s', 'before-padded.o', 'Make-commands.json', 'actual-Make-plan.txt', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_142560.c.o', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification.json', 'caller-census.json', 'proposed-guards.csv', 'closed-guard-proof.json')

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Height offset response input index changed')
 values={}
 for name,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+name.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Height offset response frozen input changed: '+name)
  values[name]=value
 return values
def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Height offset response preparation index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Height offset response evidence set changed')
 for name,h in rows.items():
  if sha((output/name).read_bytes())!=h:raise ValueError('Height offset response prepared artifact changed: '+name)
 q=json.loads((output/'preparation.json').read_text())
 if not(q['complete']and q['strict_whole_image_prediction']and q['actual_Make_object_equals_qualified']and q['neighbors']==NEIGHBORS and q['guards']==27 and q['exclusions']==0):raise ValueError('Height offset response preparation failed')
 return rows
def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Height offset response literal whole-image mismatch')
 expected=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if expected!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Height offset response named definitions changed')
def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:
  changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/retail_word_patches.us.csv':proposed_guards(values['conker/retail_word_patches.us.csv'])}
  changes['conker/build/conker.us.elf']=predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Height offset response live input changed: '+name)
 return values
def audit(root,output):
 from tools.match_progress import load_elf_functions
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or[name for name in a if a[name]!=b[name]]!=[FUNCTION]:raise ValueError('Height offset response linked neighbor/address changed')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Height offset response protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=86,frame=40,alignment_words=0,guards=27,direct_C_match=False,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result

NORMALIZED_RAW_SHA='5a5caab5388dea1aa6ba0ee12833270cfe9bd3cabbfaaf9cc3b8c23e0d641882'
NEW_GUARDS=[(0, 666763232, 666763224), (36, 2946760736, 2946760744), (60, 2409889824, 2409889832), (148, 3290955776, 3291086848), (160, 1149403136, 1149382656), (164, 1182802336, 1182801952), (168, 1182827680, 1182806560), (172, 1174942338, 1175061506), (176, 1175097600, 1175471232), (180, 1174413709, 1174442253), (184, 1141583872, 1141579776), (228, 3291611136, 3291480064), (236, 1150107648, 1150103552), (240, 1149378560, 1149390848), (244, 1182811168, 1182806048), (248, 1182802336, 1182814752), (252, 1175618178, 1175454850), (256, 1175073280, 1175601408), (260, 1174422541, 1174413709), (264, 1141866496, 1141846016), (280, 3297116284, 3297378428), (284, 1150849024, 1150844928), (292, 1182830880, 1182827040), (296, 1174807168, 1174951040), (300, 1174426125, 1174442253), (304, 1141391360, 1141383168), (340, 666697760, 666697768)]
