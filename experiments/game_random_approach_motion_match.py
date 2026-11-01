"""Random approach motion guarded C, owner and literal image audit."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_1511AF30','generated_142560'
ENTRY,ROM,BODY,SIZE=0x1511AF30,0x1483E0,332,332
SOURCE='conker/src/game/generated_142560.c'
OBJECT='conker/build/src/game/generated_142560.c.o'
ASM='conker/asm/142560.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-random-approach-motion-1511AF30-match'
RAW_SHA='bc40fb0ac41265744b4e485e32d3043dbf887581927485ab8eca2748899dd40d'
TRUTH_SHA='e3954fadc99dad334a79b4a3368bf4cf800fdc296f9aaf3badc754b4e28fc7a4'
BEFORE_ELF_SHA='8c16588be8f17bc8b6c570cf5962fe5353055af3a71d7259b915cd2085b4dc84'
BINDINGS={24: [('R_MIPS_HI16', 'D_800A3188')], 28: [('R_MIPS_LO16', 'D_800A3188')], 176: [('R_MIPS_26', 'func_150ADA20')], 228: [('R_MIPS_HI16', 'D_800A318C')], 232: [('R_MIPS_LO16', 'D_800A318C')], 236: [('R_MIPS_HI16', 'D_800A3190')], 244: [('R_MIPS_LO16', 'D_800A3190')], 280: [('R_MIPS_HI16', 'D_800A3194')], 284: [('R_MIPS_LO16', 'D_800A3194')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
HEADERS='#include <ultra64.h>\nf32 fabsf(f32);\n#pragma intrinsic (fabsf)\ns32 func_150ADA20(void);\nextern f32 D_800A3188,D_800A318C,D_800A3190,D_800A3194;\n'
SELECTED='/* Approach the command target and filter a randomized resting offset. */\nvoid func_1511AF30(u8 *state) {\n    f32 command = (f32)*(s32 *)(state + 0x3C);\n    f32 target = 75.0f * command * D_800A3188;\n    f32 current = *(f32 *)(state + 0x7C);\n    f32 delta;\n    s32 step;\n    s32 sample;\n    f32 resting;\n    f32 adjustment;\n\n    if (target != current) {\n        delta = target - current;\n        if (fabsf(delta) < 1.0f) {\n            *(f32 *)(state + 0x7C) = target;\n        } else {\n            step = delta < 0.0f ? -1 : 1;\n            *(f32 *)(state + 0x7C) = current + (f32)step;\n        }\n        *(f32 *)(state + 0x80) = 0.0f;\n    } else {\n        sample = (u32)func_150ADA20() % 1000U;\n        if (sample < 500) {\n            *(f32 *)(state + 0x84) = (f32)sample * 5.0f * command * D_800A318C * D_800A3190;\n        }\n        resting = *(f32 *)(state + 0x80);\n        adjustment = *(f32 *)(state + 0x84) - resting;\n        *(f32 *)(state + 0x80) = resting + adjustment * D_800A3194;\n    }\n    *(f32 *)state = *(f32 *)(state + 0x80) + *(f32 *)(state + 0x7C);\n}\n'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Random approach motion payload/bindings changed')
 return raw,bindings
def recovered_owner(before):
 old='s32 func_1511AF30() {\n    return 0;\n}'
 if before.count(old)!=1:raise ValueError('Random approach placeholder changed')
 if before.count('#pragma intrinsic (fabsf)')!=1:raise ValueError('Existing fabsf intrinsic changed')
 declarations='\n'.join(line for line in HEADERS.splitlines()[1:]if line not in('f32 fabsf(f32);','#pragma intrinsic (fabsf)'))+'\n\n'
 return before.replace(old,declarations+SELECTED.rstrip(),1)


def normalized_payload(raw,bindings):
 checked_payload(raw,bindings);w=list(struct.unpack('>83I',raw));result=w[:]
 # Exchange the two FP colors over the closed target/delta lifetime.
 # Neither is live on entry; after the comparison they are caller-saved dead values.
 color=lambda f:{2:12,12:2}.get(f,f)
 for i in range(0x30//4,0x7C//4):
  word=w[i];op=word>>26
  if op==17 and word>>21&31==16:
   result[i]=(word&~((31<<16)|(31<<11)|(31<<6)))|(color(word>>16&31)<<16)|(color(word>>11&31)<<11)|(color(word>>6&31)<<6)
  elif op in(49,57):result[i]=(word&~(31<<16))|(color(word>>16&31)<<16)
 # Restore original operand order for two commutative floating additions.
 for at in(0x9C,0x128):
  word=result[at//4]
  if word>>26!=17 or word>>21&31!=16 or word&63!=0:raise ValueError('Random approach floating add changed')
  result[at//4]=(word&~((31<<16)|(31<<11)))|((word>>11&31)<<16)|((word>>16&31)<<11)
 answer=struct.pack('>83I',*result)
 if sha(answer)!=NORMALIZED_RAW_SHA:raise ValueError('Random approach closed FP transform failed')
 return answer

def derive_guards(raw,bindings):
 normalized=normalized_payload(raw,bindings);rows=[(i,struct.unpack_from('>I',raw,i)[0],struct.unpack_from('>I',normalized,i)[0])for i in range(0,BODY,4)if raw[i:i+4]!=normalized[i:i+4]]
 if len(rows)!=8:raise ValueError('Random approach guard count changed')
 return rows

def proposed_guards(before):
 prefix=(OWNER+','+FUNCTION+',').encode()
 if any(v.startswith(prefix) for v in before.splitlines()):raise ValueError('Random approach guards already present')
 newline=b'\r\n' if b'\r\n' in before else b'\n'
 if not before.endswith(newline):raise ValueError('Random approach guard manifest newline changed')
 return before+b''.join(('%s,%s,0x%03X,0x%08X,0x%08X,-,-,Normalize random approach closed FP registers and operand order,,,false'%(OWNER,FUNCTION,at,a,b)).encode()+newline for at,a,b in NEW_GUARDS)

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
 if a!=b:raise ValueError(('Random approach owner diagnostics changed',a-b,b-a))
 return dict(before=sum(a.values()),after=sum(b.values()),removed=0)

def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Random approach motion predictor baseline changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Random approach motion predecessor extent changed')
 struct.pack_into('>I',result,rows[0][0]+8,BODY)
 all_rows={at:(name,fields,string)for at,name,fields,string in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  originals=[];start=all_rows[first][2]
  for j,name in enumerate(names):
   at=first+16*j;actual,fields,string=all_rows[at]
   if actual!=name or fields[1:]!=(int(name[2:],16),0,16,0,0xFFF1 if name in('D_800A3188','D_800A318C','D_800A3190','D_800A3194')else 6):raise ValueError('Random approach metadata definition changed')
   if string!=start+11*j:raise ValueError('Random approach metadata strings changed')
   originals.append(before[at+4:at+16])
  text=b''.join(n.encode()+b'\0'for n in names)
  if before[start:start+len(text)]!=text or sorted(order)!=list(range(len(names))):raise ValueError('Random approach metadata group changed')
  for j,k in enumerate(order):result[first+16*j+4:first+16*j+16]=originals[k]
  result[start:start+len(text)]=b''.join(names[k].encode()+b'\0'for k in order)
 return bytes(result)

SNAPSHOT_SHA='47a48034d3c219ecb05e74dd778a44a33a2a0343bcbb1d8e9ad87ba3d7c04bf5'
PREPARED_SHA='d40867d89f106d4629d06e47c7d97735909e451a3bd31183bbb208098c49dd5c'
NEIGHBORS=83
EVIDENCE=('selected-final.o', 'selected-final.c', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_1511AF30.o', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner-diagnostics.txt', 'proposed-owner.c', 'qualified-padded.o', 'qualified-padded.s', 'before-padded.o', 'Make-commands.json', 'actual-Make-plan.txt', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_142560.c.o', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification.json', 'caller-census.json', 'proposed-guards.csv', 'closed-guard-proof.json')

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Random approach motion input index changed')
 values={}
 for name,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+name.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Random approach motion frozen input changed: '+name)
  values[name]=value
 return values
def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Random approach motion preparation index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Random approach motion evidence set changed')
 for name,h in rows.items():
  if sha((output/name).read_bytes())!=h:raise ValueError('Random approach motion prepared artifact changed: '+name)
 q=json.loads((output/'preparation.json').read_text())
 if not(q['complete']and q['strict_whole_image_prediction']and q['actual_Make_object_equals_qualified']and q['neighbors']==NEIGHBORS and q['guards']==8 and q['exclusions']==0):raise ValueError('Random approach motion preparation failed')
 return rows
def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Random approach motion literal whole-image mismatch')
 expected=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if expected!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Random approach motion named definitions changed')
def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:
  changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/retail_word_patches.us.csv':proposed_guards(values['conker/retail_word_patches.us.csv'])}
  changes['conker/build/conker.us.elf']=predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Random approach motion live input changed: '+name)
 return values
def audit(root,output):
 from tools.match_progress import load_elf_functions
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or[name for name in a if a[name]!=b[name]]!=[FUNCTION]:raise ValueError('Random approach motion linked neighbor/address changed')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Random approach motion protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=83,frame=32,alignment_words=0,guards=8,direct_C_match=False,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result

NORMALIZED_RAW_SHA='99ade92fbad1a19ffb0eb040f0a05fd31d9ada4c3597f6b1289dcccf42ac0f26'
NEW_GUARDS=[(48, 1175076994, 1175077634), (52, 1175326770, 1175347250), (68, 1175327489, 1175347329), (84, 1174429701, 1174409221), (108, 3833725052, 3834380412), (120, 1175609404, 1175588924), (156, 1175335424, 1174827520), (296, 1174426624, 1175061504)]

METADATA_GROUPS=(
 (0x2A65B4,('D_800A3190','D_800ACE90','D_8009E7C0'),(1,2,0)),
 (0x2A7C74,('D_800A3194','D_80091894','D_8009E7C4'),(1,2,0)),
 (0x2C6D34,('D_800A318C','D_8009E7BC'),(1,0)),
 (0x2CAB24,('D_800A3188','D_800A74D8','D_80091888','D_8009E7B8'),(1,2,3,0)),
)
