"""Packed cosine motion guarded C, owner and literal image audit."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_151163C0','generated_142560'
ENTRY,ROM,BODY,SIZE=0x151163C0,0x143870,332,332
SOURCE='conker/src/game/generated_142560.c'
OBJECT='conker/build/src/game/generated_142560.c.o'
ASM='conker/asm/142560.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-packed-cosine-motion-151163C0-match'
RAW_SHA='21fa35697d8e80ff339c60af33cd9cc14d3fcec9c8941dc8268da4c54521cd35'
TRUTH_SHA='7e9cf489bd4a09f8954f29640baf5fa8469f8a18a64fcec31385942e846cfadc'
BEFORE_ELF_SHA='2efb08f7b5e074126e40815fe101d5297eaa5f4e6e5a0519079f6b7df1d22fd8'
BINDINGS={96: [('R_MIPS_HI16', 'D_800A2FB0')], 104: [('R_MIPS_LO16', 'D_800A2FB0')], 152: [('R_MIPS_26', 'cosf')], 168: [('R_MIPS_HI16', 'D_800A2FB4')], 196: [('R_MIPS_LO16', 'D_800A2FB4')], 204: [('R_MIPS_26', 'cosf')], 220: [('R_MIPS_HI16', 'D_800BE9E4')], 228: [('R_MIPS_LO16', 'D_800BE9E4')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
HEADERS='#include <ultra64.h>\nextern s32 D_800BE9E4;\nextern f32 D_800A2FB0,D_800A2FB4;\n'
SELECTED='/* Apply the packed cosine amplitudes and phase steps, then publish both deltas. */\nvoid func_151163C0(u8 *state) {\n    f32 amplitude = (f32)((*(s32 *)(state + 0x3C)) & 0xFF);\n    u32 firstStep = ((*(s32 *)(state + 0x3C)) >> 16) & 0xFF;\n    u32 secondStep = ((*(s32 *)(state + 0x3C)) >> 24) & 0xFF;\n    f32 angleAmplitude = (f32)(u32)(((*(s32 *)(state + 0x3C)) >> 8) & 0xFF) * 1.40625f;\n    s16 previousY = *(s16 *)(state + 0x12);\n    f32 previousAngle = *(f32 *)state;\n    f32 angle;\n\n    *(f32 *)(state + 0x18) = cosf((f32)*(s32 *)(state + 0x7C) * D_800A2FB0) * amplitude;\n    angle = cosf((f32)*(s32 *)(state + 0x80) * D_800A2FB4) * angleAmplitude;\n    *(f32 *)state = angle;\n    *(u32 *)(state + 0x7C) += firstStep * (u32)D_800BE9E4;\n    *(u32 *)(state + 0x80) += secondStep * (u32)D_800BE9E4;\n    *(s16 *)(state + 0x5C) = *(s16 *)(state + 0x12) - previousY;\n    *(f32 *)(state + 0x60) = angle - previousAngle;\n}\n'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Packed cosine motion payload/bindings changed')
 return raw,bindings
def recovered_owner(before):
 old='s32 func_151163C0() {\n    return 0;\n}'
 if before.count(old)!=1:raise ValueError('Packed cosine placeholder changed')
 if 'D_800A2FB0'in before or 'D_800A2FB4'in before:raise ValueError('Packed cosine globals already declared')
 return before.replace(old,'extern f32 D_800A2FB0, D_800A2FB4;\n\n'+SELECTED.rstrip(),1)


def normalized_payload(raw,bindings):
 checked_payload(raw,bindings);w=list(struct.unpack('>83I',raw));result=w[:]
 # The first amplitude's integer dies at its MTC1. Reuse that dead temporary
 # for the first phase step only after its float value has been captured.
 result[4]=(w[4]&~0x001F0000)|(24<<16)
 result[5]=(w[5]&~0x001F0000)|(24<<16)
 result[10]=(w[10]&~0x0000F800)|(14<<11)
 result[12]=(w[12]&~0x03FF0000)|(14<<21)|(15<<16)
 # Independent stack words: amplitude at SP+2C and phase step at SP+28.
 result[14]=(w[15]&~0x001F0000)|(15<<16);result[15]=w[14]
 answer=struct.pack('>83I',*result)
 if sha(answer)!=NORMALIZED_RAW_SHA:raise ValueError('Packed cosine closed transformation failed')
 return answer

def derive_guards(raw,bindings):
 normalized=normalized_payload(raw,bindings);rows=[(i,struct.unpack_from('>I',raw,i)[0],struct.unpack_from('>I',normalized,i)[0])for i in range(0,BODY,4)if raw[i:i+4]!=normalized[i:i+4]]
 if len(rows)!=6:raise ValueError('Packed cosine guard count changed')
 return rows

def proposed_guards(before):
 prefix=(OWNER+','+FUNCTION+',').encode()
 if any(v.startswith(prefix) for v in before.splitlines()):raise ValueError('Packed cosine guards already present')
 newline=b'\r\n' if b'\r\n' in before else b'\n'
 if not before.endswith(newline):raise ValueError('Packed cosine guard manifest newline changed')
 return before+b''.join(('%s,%s,0x%03X,0x%08X,0x%08X,-,-,Normalize packed cosine dead temporaries and independent capture stores,,,false'%(OWNER,FUNCTION,at,a,b)).encode()+newline for at,a,b in NEW_GUARDS)

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
 if sha(before)!=BEFORE_ELF_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Packed cosine motion predictor baseline changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Packed cosine motion predecessor extent changed')
 struct.pack_into('>I',result,rows[0][0]+8,BODY)

 return bytes(result)

SNAPSHOT_SHA='8ce93113dfae68896b60d14016f444050eded5f6dcca774ead07de56c9b94022'
PREPARED_SHA='ecc09c49b1e27c1da6e5e2a39ebc359b629523f940688adbfb3333542f65cfb2'
NEIGHBORS=83
EVIDENCE=('selected-final.o', 'selected-final.c', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_151163C0.o', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner-diagnostics.txt', 'proposed-owner.c', 'qualified-padded.o', 'qualified-padded.s', 'before-padded.o', 'Make-commands.json', 'actual-Make-plan.txt', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_142560.c.o', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification.json', 'caller-census.json', 'proposed-guards.csv', 'closed-guard-proof.json')

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Packed cosine motion input index changed')
 values={}
 for name,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+name.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Packed cosine motion frozen input changed: '+name)
  values[name]=value
 return values
def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Packed cosine motion preparation index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Packed cosine motion evidence set changed')
 for name,h in rows.items():
  if sha((output/name).read_bytes())!=h:raise ValueError('Packed cosine motion prepared artifact changed: '+name)
 q=json.loads((output/'preparation.json').read_text())
 if not(q['complete']and q['strict_whole_image_prediction']and q['actual_Make_object_equals_qualified']and q['neighbors']==NEIGHBORS and q['guards']==6 and q['exclusions']==0):raise ValueError('Packed cosine motion preparation failed')
 return rows
def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Packed cosine motion literal whole-image mismatch')
 expected=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if expected!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Packed cosine motion named definitions changed')
def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:
  changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/retail_word_patches.us.csv':proposed_guards(values['conker/retail_word_patches.us.csv'])}
  changes['conker/build/conker.us.elf']=predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Packed cosine motion live input changed: '+name)
 return values
def audit(root,output):
 from tools.match_progress import load_elf_functions
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or[name for name in a if a[name]!=b[name]]!=[FUNCTION]:raise ValueError('Packed cosine motion linked neighbor/address changed')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Packed cosine motion protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=83,frame=48,alignment_words=0,guards=6,direct_C_match=False,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result

NORMALIZED_RAW_SHA='6a8fd6676337c2bfa4d1f8549ca80c19cfc8de461e4617f6bd50556d4ae44d4f'
NEW_GUARDS=[(16, 810418431, 811073791), (20, 1150164992, 1150820352), (40, 162819, 160771), (48, 838336767, 835649791), (56, 3886415916, 2947481640), (60, 2948071464, 3886415916)]
