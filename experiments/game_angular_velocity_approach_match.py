"""Angular velocity approach guarded C, owner and literal image audit."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_15116D7C','generated_142560'
ENTRY,ROM,BODY,SIZE=0x15116D7C,0x14422C,296,296
SOURCE='conker/src/game/generated_142560.c'
OBJECT='conker/build/src/game/generated_142560.c.o'
ASM='conker/asm/142560.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-angular-velocity-approach-15116D7C-match'
RAW_SHA='19a4a4eac9c99cc627d5e8cfa760e88a85fb7ba3f7cfae38e76e59df22eba0ea'
TRUTH_SHA='122cfd48eb57084183bbe6b5d109d25fb532fd4dfb4dbbcf7016527a2e264c77'
BEFORE_ELF_SHA='83346e7617b975a65e7af47e5b417a10b000edfe9f396728160827d438f36c42'
BINDINGS={4:[('R_MIPS_HI16','D_800BE9E4')],8:[('R_MIPS_LO16','D_800BE9E4')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
HEADERS='#include <ultra64.h>\nextern s32 D_800BE9E4;\n'
SELECTED='/* Approach three target angular velocities and wrap each updated angle once. */\nvoid func_15116D7C(u8 *state) {\n    f32 maxStep = (f32)*(s32 *)(state + 0x3C) * 0.00390625f;\n    f32 ticks = (f32)D_800BE9E4;\n    s32 offset = 0;\n    f32 *angle = (f32 *)state;\n    f32 *velocity = (f32 *)(state + 0x60);\n    f32 *desired = (f32 *)(state + 0x7C);\n\n    do {\n        if (*desired != *velocity) {\n            if (*velocity > *desired) {\n                *velocity -= maxStep;\n                if (*velocity < *desired) {\n                    *velocity = *desired;\n                }\n            } else {\n                *velocity += maxStep;\n                if (*velocity > *desired) {\n                    *velocity = *desired;\n                }\n            }\n        }\n        *angle += *velocity * ticks;\n        if (*angle < 0.0f) {\n            *angle += 360.0f;\n        } else if (*angle >= 360.0f) {\n            *angle -= 360.0f;\n        }\n        velocity++;\n        desired++;\n        angle++;\n        offset += 4;\n    } while (offset != 12);\n}\n'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Angular velocity approach payload/bindings changed')
 return raw,bindings
def recovered_owner(before):
 old='s32 func_15116D7C() {\n    return 0;\n}'
 if before.count(old)!=1:raise ValueError('Angular velocity old stub changed')
 return before.replace(old,SELECTED.rstrip(),1)

def normalized_payload(raw,bindings):
 checked_payload(raw,bindings);words=list(struct.unpack('>74I',raw));result=words[:]
 # The incoming A0 remains a record pointer through both pointer initializers.
 # Move counter initialization before angle capture, then apply the closed
 # loop register map: raw V0(counter)->V1, V1(angle)->A3, A0(limit)->V0.
 result[13]=0x00001825;result[16]=0x00803825;result[17]=0x2402000C
 result[18],result[19]=words[19],words[18]
 mapping={2:3,3:7,4:2}
 for i in range(20,74):
  word=words[i];op=word>>26
  if op in (9,4,5):
   rs,rt=word>>21&31,word>>16&31;word=(word&~0x03FF0000)|(mapping.get(rs,rs)<<21)|(mapping.get(rt,rt)<<16)
  elif op in(0x31,0x39):
   rs=word>>21&31;word=(word&~0x03E00000)|(mapping.get(rs,rs)<<21)
  result[i]=word
 # Equality is symmetric; retain retail's operand spelling after load swap.
 if words[21]!=0x460E6032:raise ValueError('Angular opening equality changed')
 result[21]=0x460C7032
 answer=struct.pack('>74I',*result)
 if sha(answer)!='1cb6ba9723f3a2bcebdc067375971b0ad65cbee50700f32a8def5ea859dbd933':raise ValueError('Angular closed raw transformation failed')
 return answer

def derive_guards(raw,bindings):
 normalized=normalized_payload(raw,bindings)
 rows=[(i,struct.unpack_from('>I',raw,i)[0],struct.unpack_from('>I',normalized,i)[0]) for i in range(0,BODY,4) if raw[i:i+4]!=normalized[i:i+4]]
 if len(rows)!=14:raise ValueError('Angular closed guard count changed')
 return rows

def proposed_guards(before):
 prefix=(OWNER+','+FUNCTION+',').encode()
 if any(v.startswith(prefix) for v in before.splitlines()):raise ValueError('Angular guards already present')
 newline=b'\r\n' if b'\r\n' in before else b'\n'
 if not before.endswith(newline):raise ValueError('Angular guard manifest newline changed')
 return before+b''.join(('%s,%s,0x%03X,0x%08X,0x%08X,-,-,Normalize angular velocity closed loop register and independent opening schedule,,,false'%(OWNER,FUNCTION,at,a,b)).encode()+newline for at,a,b in NEW_GUARDS)

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
 if sha(before)!=BEFORE_ELF_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Angular velocity approach predictor baseline changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Angular velocity approach predecessor extent changed')
 struct.pack_into('>I',result,rows[0][0]+8,BODY)

 return bytes(result)

SNAPSHOT_SHA='42d4cedd10b5bf71c42642b226c434e5012498831be877b5fc6b3b16c311b3fd'
PREPARED_SHA='274ca93a0621061a7f87dfea0fd1447be098176242ea17cd9348832710687210'
NEIGHBORS=83
EVIDENCE=('selected-final.o', 'selected-final.c', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_15116D7C.o', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner-diagnostics.txt', 'proposed-owner.c', 'qualified-padded.o', 'qualified-padded.s', 'before-padded.o', 'Make-commands.json', 'actual-Make-plan.txt', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_142560.c.o', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification.json', 'caller-census.json', 'proposed-guards.csv', 'closed-guard-proof.json')

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Angular velocity approach input index changed')
 values={}
 for name,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+name.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Angular velocity approach frozen input changed: '+name)
  values[name]=value
 return values
def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Angular velocity approach preparation index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Angular velocity approach evidence set changed')
 for name,h in rows.items():
  if sha((output/name).read_bytes())!=h:raise ValueError('Angular velocity approach prepared artifact changed: '+name)
 q=json.loads((output/'preparation.json').read_text())
 if not(q['complete']and q['strict_whole_image_prediction']and q['actual_Make_object_equals_qualified']and q['neighbors']==NEIGHBORS and q['guards']==14 and q['exclusions']==0):raise ValueError('Angular velocity approach preparation failed')
 return rows
def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Angular velocity approach literal whole-image mismatch')
 expected=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if expected!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Angular velocity approach named definitions changed')
def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:
  changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/retail_word_patches.us.csv':proposed_guards(values['conker/retail_word_patches.us.csv'])}
  changes['conker/build/conker.us.elf']=predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Angular velocity approach live input changed: '+name)
 return values
def audit(root,output):
 from tools.match_progress import load_elf_functions
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or[name for name in a if a[name]!=b[name]]!=[FUNCTION]:raise ValueError('Angular velocity approach linked neighbor/address changed')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Angular velocity approach protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=74,frame=0,alignment_words=0,guards=14,direct_C_match=False,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result

NEW_GUARDS=[(52, 8394789, 6181), (64, 4133, 8402981), (68, 604241932, 604110860), (72, 3301703680, 3299737600), (76, 3299737600, 3301703680), (80, 608305156, 610467844), (84, 1175347250, 1175220274), (204, 3295150080, 3303538688), (220, 3831758848, 3840147456), (224, 3295412224, 3303800832), (252, 3831889920, 3840278528), (276, 3832020992, 3840409600), (280, 340066251, 342032331), (284, 610467844, 619118596)]
