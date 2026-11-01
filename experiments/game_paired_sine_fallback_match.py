"""Paired sine fallback guarded C, owner and literal image audit."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_1511C548','generated_142560'
ENTRY,ROM,BODY,SIZE=0x1511C548,0x1499F8,240,240
SOURCE='conker/src/game/generated_142560.c'
OBJECT='conker/build/src/game/generated_142560.c.o'
ASM='conker/asm/142560.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-paired-sine-fallback-1511C548-match'
RAW_SHA='0d4b5aed919b64674400df4ed806030c72cd50bc655dca5f84184ed5a3baf5f9'
TRUTH_SHA='44e6f01ccff0b01baf81d89efe0206bf3a5336e877bc77f7ec46435b0f14969b'
BEFORE_ELF_SHA='129eb8fb267665051c47daae2a7448a42f01513487c573b48da7b11593b1bb78'
BINDINGS={16: [('R_MIPS_26', 'sinf')], 28: [('R_MIPS_26', 'sinf')], 48: [('R_MIPS_HI16', 'D_800BE9A4')], 52: [('R_MIPS_LO16', 'D_800BE9A4')], 60: [('R_MIPS_HI16', 'D_800A31EC')], 84: [('R_MIPS_LO16', 'D_800A31EC')], 88: [('R_MIPS_HI16', 'D_800A31F0')], 112: [('R_MIPS_LO16', 'D_800A31F0')], 128: [('R_MIPS_26', 'func_15144B68')], 140: [('R_MIPS_26', 'func_15144B68')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
HEADERS='#include <ultra64.h>\nextern f32 D_800BE9A4,D_800A31EC,D_800A31F0;\nf32 func_15144B68(f32);\n'
SELECTED='/* Update paired sine outputs and wrapped phases, preserving the zero fallback. */\nvoid func_1511C548(u8 *state) {\n    f32 second;\n    f32 first;\n\n    first = sinf(*(f32 *)(state + 0x80));\n    second = sinf(*(f32 *)(state + 0x84));\n    *(f32 *)state = first * 16.0f;\n    *(f32 *)(state + 8) = second * 16.0f;\n    *(f32 *)(state + 0x80) += D_800A31EC * D_800BE9A4;\n    *(f32 *)(state + 0x84) += D_800A31F0 * D_800BE9A4;\n    *(f32 *)(state + 0x80) = func_15144B68(*(f32 *)(state + 0x80));\n    *(f32 *)(state + 0x84) = func_15144B68(*(f32 *)(state + 0x84));\n    if (0.0f == *(f32 *)(state + 8) && 0.0f == *(f32 *)(state + 0x84)) {\n        *(f32 *)state = 7.5f;\n        *(f32 *)(state + 8) = 8.0f;\n    }\n}\n'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Paired sine fallback payload/bindings changed')
 return raw,bindings
def recovered_owner(before):
 old='s32 func_1511C548() {\n    return 0;\n}'
 if before.count(old)!=1:raise ValueError('Paired sine placeholder changed')
 declarations='\n'.join(HEADERS.splitlines()[1:])+'\n\n'
 return before.replace(old,declarations+SELECTED.rstrip(),1)


def normalized_payload(raw,bindings):
 checked_payload(raw,bindings);w=list(struct.unpack('>60I',raw));result=w[:]
 # The wrap result store (+84/F0) and Z load (+8/F6) use disjoint
 # addresses and FP registers. Preserve the retail independent order.
 if(w[38],w[39])!=(0xC6060008,0xE6000084):raise ValueError('Paired sine independent operations changed')
 result[38],result[39]=w[39],w[38];answer=struct.pack('>60I',*result)
 if sha(answer)!=NORMALIZED_RAW_SHA:raise ValueError('Paired sine independent schedule failed')
 return answer

def derive_guards(raw,bindings):
 normalized=normalized_payload(raw,bindings);rows=[(i,struct.unpack_from('>I',raw,i)[0],struct.unpack_from('>I',normalized,i)[0])for i in range(0,BODY,4)if raw[i:i+4]!=normalized[i:i+4]]
 if len(rows)!=2:raise ValueError('Paired sine guard count changed')
 return rows

def proposed_guards(before):
 prefix=(OWNER+','+FUNCTION+',').encode()
 if any(v.startswith(prefix) for v in before.splitlines()):raise ValueError('Paired sine guards already present')
 newline=b'\r\n' if b'\r\n' in before else b'\n'
 if not before.endswith(newline):raise ValueError('Paired sine guard manifest newline changed')
 return before+b''.join(('%s,%s,0x%03X,0x%08X,0x%08X,-,-,Normalize paired sine independent output store and load,,,false'%(OWNER,FUNCTION,at,a,b)).encode()+newline for at,a,b in NEW_GUARDS)

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
 if a!=b:raise ValueError(('Paired sine owner diagnostics changed',a-b,b-a))
 return dict(before=sum(a.values()),after=sum(b.values()),removed=0)

def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Paired sine fallback predictor baseline changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Paired sine fallback predecessor extent changed')
 struct.pack_into('>I',result,rows[0][0]+8,BODY)
 # GNU ld reverses one closed, equal-length global-symbol serialization pair.
 # Predict complete rows and string bytes; no metadata region is excluded.
 first,second=0x2B1A34,0x2B1A44
 if before[first:second+16]!=bytes.fromhex('00014ee1800c6360000000001000fff100014eec8009e6a00000000010000006'):
  raise ValueError('Paired sine symbol serialization predecessor changed')
 result[first+4:first+16]=before[second+4:second+16]
 result[second+4:second+16]=before[first+4:first+16]
 names=0x2f4e95;old=b'D_800C6360\0D_8009E6A0\0'
 if before[names:names+len(old)]!=old:raise ValueError('Paired sine symbol-name pair changed')
 result[names:names+len(old)]=b'D_8009E6A0\0D_800C6360\0'
 return bytes(result)

SNAPSHOT_SHA='63cd208288fef482afd3dbfdaf5b8535c209c4dc45487f877be95f8fef680959'
PREPARED_SHA='63b0c6021570963b21cbf505d785f58f55105b8a7d596112733cc1df79f7a721'
NEIGHBORS=83
EVIDENCE=('selected-final.o', 'selected-final.c', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_1511C548.o', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner-diagnostics.txt', 'proposed-owner.c', 'qualified-padded.o', 'qualified-padded.s', 'before-padded.o', 'Make-commands.json', 'actual-Make-plan.txt', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_142560.c.o', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification.json', 'caller-census.json', 'proposed-guards.csv', 'closed-guard-proof.json')

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Paired sine fallback input index changed')
 values={}
 for name,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+name.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Paired sine fallback frozen input changed: '+name)
  values[name]=value
 return values
def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Paired sine fallback preparation index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Paired sine fallback evidence set changed')
 for name,h in rows.items():
  if sha((output/name).read_bytes())!=h:raise ValueError('Paired sine fallback prepared artifact changed: '+name)
 q=json.loads((output/'preparation.json').read_text())
 if not(q['complete']and q['strict_whole_image_prediction']and q['actual_Make_object_equals_qualified']and q['neighbors']==NEIGHBORS and q['guards']==2 and q['exclusions']==0):raise ValueError('Paired sine fallback preparation failed')
 return rows
def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Paired sine fallback literal whole-image mismatch')
 expected=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if expected!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Paired sine fallback named definitions changed')
def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:
  changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/retail_word_patches.us.csv':proposed_guards(values['conker/retail_word_patches.us.csv'])}
  changes['conker/build/conker.us.elf']=predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Paired sine fallback live input changed: '+name)
 return values
def audit(root,output):
 from tools.match_progress import load_elf_functions
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or[name for name in a if a[name]!=b[name]]!=[FUNCTION]:raise ValueError('Paired sine fallback linked neighbor/address changed')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Paired sine fallback protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=60,frame=40,alignment_words=0,guards=2,direct_C_match=False,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result

NORMALIZED_RAW_SHA='f2b887e67c96cbcc2c7c9a4251e396b058a1abf104ce5e2f44c2e828270d83ba'
NEW_GUARDS=[(152, 3322281992, 3858759812), (156, 3858759812, 3322281992)]
