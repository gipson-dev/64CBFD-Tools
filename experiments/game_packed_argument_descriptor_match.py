"""Packed argument descriptor: complete direct C, exact bindings and whole-image qualification."""
from pathlib import Path
from collections import Counter
import csv,hashlib,io,json,struct
from tools.experiments.game_remaining_donor_candidates import function_span,compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions
import sys
import tools.pad_generated_object as pad
sys.modules.setdefault("pad_generated_object",pad)
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
FUNCTION,OWNER='func_1510A930','generated_137DE0'
SOURCE='conker/src/game/generated_137DE0.c'
OBJECT='conker/build/src/game/generated_137DE0.c.o'
ASM='conker/asm/137DE0.s'
BUILD='conker/build/game-packed-argument-descriptor-1510A930-match'
ENTRY,ROM,BODY,SIZE=0x1510A930,0x137DE0,228,240
RAW_SHA='4e941fb02d598200f47b0409c7c4e51c9b451a9fe4168a0932d50d5fe1ee726c'
NORMALIZED_SHA='4e941fb02d598200f47b0409c7c4e51c9b451a9fe4168a0932d50d5fe1ee726c'
TRUTH_SHA='f048214a4d26752e1dfeaf1b1c0ff9759fba02ed1a9372939a2f80d21ce44acb'
BEFORE_ELF_SHA='ed315d5acc97e7491d314ae9e54d47e0b46bbfdcdc8fc97a72e0b4c9398681cf'
GUARD_SHA='173f3280db84aff3022faeb4a612900e42e80e9cd2d483fdfe90819bdeb63b92'
SNAPSHOT_SHA='51e599f55be82efd9754b095d8a8e3a91090e5d2e928b8d3a3051d23dbc01978'
BINDINGS={12: [('R_MIPS_HI16', 'D_800917EC')], 24: [('R_MIPS_LO16', 'D_800917EC')], 64: [('R_MIPS_HI16', 'D_800A26A0')], 68: [('R_MIPS_LO16', 'D_800A26A0')], 204: [('R_MIPS_26', 'func_15169968')]}
sha=lambda data:hashlib.sha256(data).hexdigest()
HEADERS='#include <ultra64.h>\nextern u8 D_800917EC[];\nextern f32 D_800A26A0;\nvoid *func_15169968(void *);\ntypedef struct {\n    u8 *asset;\n    u32 retained04;\n    u32 packedFirstSecond;\n    u32 packedThirdSum;\n    s32 field10;\n    s16 sum;\n    s16 field16;\n    s16 field18;\n    u8 retained1A[2];\n    f32 field1C;\n    f32 field20;\n    s16 field24,field26,field28,field2A,field2C,field2E;\n    u8 field30,field31,field32,field33,field34,field35,field36,field37;\n    u8 retained38;\n    u8 field39;\n    u8 retained3A[2];\n} PackedArgumentDescriptor;\n\n'
DECLARATIONS='extern u8 D_800917EC[];\nextern f32 D_800A26A0;\nvoid *func_15169968(void *);\ntypedef struct {\n    u8 *asset;\n    u32 retained04;\n    u32 packedFirstSecond;\n    u32 packedThirdSum;\n    s32 field10;\n    s16 sum;\n    s16 field16;\n    s16 field18;\n    u8 retained1A[2];\n    f32 field1C;\n    f32 field20;\n    s16 field24,field26,field28,field2A,field2C,field2E;\n    u8 field30,field31,field32,field33,field34,field35,field36,field37;\n    u8 retained38;\n    u8 field39;\n    u8 retained3A[2];\n} PackedArgumentDescriptor;\n\n'
SELECTED='/* Pack three argument words and their wrapping sum into the copied descriptor. */\nvoid *func_1510A930(u32 first,u32 second,u32 third) {\n    PackedArgumentDescriptor descriptor;\n    u32 sum=first+second+third;\n    u32 packed=(first<<16)|second;\n    descriptor.asset=D_800917EC;\n    descriptor.field30=10;\n    descriptor.field2C=64;\n    descriptor.field2E=32;\n    descriptor.field28=0x18FC;\n    descriptor.field2A=0x1A12;\n    descriptor.field36=7;\n    descriptor.field39=0;\n    descriptor.packedFirstSecond=packed;\n    descriptor.packedThirdSum=(third<<16)|sum;\n    descriptor.field10=10000;\n    descriptor.sum=sum;\n    descriptor.field18=0;\n    descriptor.field24=0;\n    descriptor.field26=0;\n    descriptor.field31=1;\n    descriptor.field32=255;\n    descriptor.field33=255;\n    descriptor.field34=255;\n    descriptor.field37=17;\n    descriptor.field35=0;\n    descriptor.field16=0;\n    descriptor.field1C=228.0f;\n    descriptor.field20=D_800A26A0;\n    return func_15169968(&descriptor);\n}\n'
NEW_GUARDS=[]

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Packed argument descriptor compiler payload or ABI bindings changed')
 return raw,bindings

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Packed argument descriptor scope changed')
 return checked_payload(raw,bindings)

def guard_manifest(before):
 if sha(before)!=GUARD_SHA:raise ValueError('Packed argument descriptor inherited guards changed')
 return before

def recovered_owner(before):
 if before!='#include <ultra64.h>\n\n/* Non-matching placeholders for the text-only asm slice asm/137DE0.s. */\n\ns32 func_1510A930() {\n    return 0;\n}\n':raise ValueError("Packed descriptor placeholder changed")
 return HEADERS+SELECTED

LAYOUT=ASM

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Packed argument descriptor snapshot changed')
 values={}
 for n,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Packed argument descriptor frozen input changed: '+n)
  values[n]=value
 if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Packed argument descriptor predecessor image changed')
 return values

METADATA_PAIR=(0x29F174,('D_800A26A0','D_800E0BAC'),0x2E5A92)

def reorder_metadata(before,result):
 at,names,string_at=METADATA_PAIR
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 group=[rows[at+16*i]for i in range(2)]
 if tuple(n for n,f,s in group)!=names or tuple(s for n,f,s in group)!=(string_at,string_at+11):raise ValueError('Packed descriptor metadata pair changed')
 expected=b''.join(n.encode()+b'\0'for n in names)
 if before[string_at:string_at+22]!=expected:raise ValueError('Packed descriptor metadata strings changed')
 result[string_at:string_at+22]=b''.join(n.encode()+b'\0'for n in reversed(names))
 for i in range(2):struct.pack_into('>IIIBBH',result,at+16*i,group[i][1][0],*group[1-i][1][1:])
 return result

def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Packed argument descriptor predictor inputs changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 matches=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(matches)!=1 or matches[0][2][1:3]!=(ENTRY,12):raise ValueError('Packed argument descriptor predecessor symbol changed')
 struct.pack_into('>I',result,matches[0][0]+8,BODY)
 return bytes(reorder_metadata(before,result))

def check_image(before,actual,truth):
 expected=predicted_image(before,truth)
 if expected!=actual:raise ValueError('Packed argument descriptor strict whole-image prediction differs')
 definitions=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if definitions!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Packed argument descriptor named definitions changed')

def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Packed argument descriptor live input changed: '+name)
 return values



PREPARED_SHA='ab60e28560a9cf87287f3e0398eacd8343a6930944a951850843ef78bbe9d5e0'
EVIDENCE=('before-padded.o', 'qualified-padded.o', 'qualified-padded.s', 'proposed-owner.c', 'proposed-guards.csv', 'selected-semantic-input.c', 'selected-final.c', 'selected-final.o', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_1510A930.o', 'before-owner.o', 'before-owner.c', 'before-owner-processed.c', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner.c', 'after-owner-processed.c', 'after-owner-diagnostics.txt', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_137DE0.c.o', 'make-shadow/src/game/generated_137DE0.c.o.compact', 'make-shadow/src/game/generated_137DE0.c.o.padded.s', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification-v9.json', 'native-descriptor.json')

def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Packed argument descriptor prepared evidence index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Packed argument descriptor prepared evidence set changed')
 for name,wanted in rows.items():
  if sha((output/name).read_bytes())!=wanted:raise ValueError('Packed argument descriptor prepared evidence changed: '+name)
 for name in ('selected-final','before-owner','after-owner','actual-Make'):
  if (output/(name+'-diagnostics.txt')).read_bytes():raise ValueError('Packed argument descriptor owner diagnostics changed')
 if (output/'make-shadow/src/game/generated_137DE0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Packed argument descriptor actual Make object changed')
 q=json.loads((output/'preparation.json').read_text())
 if not all(q[k] for k in ('complete','normal_O2_g3','owner_diagnostics_empty','actual_Make_object_equals_qualified','strict_whole_image_prediction','all_function_addresses_fixed')) or q['guards']!=0 or q['guard_preimage_controls']!=0 or q['exclusions']!=0:raise ValueError('Packed argument descriptor private preparation failed')
 return rows

def audit(root,output):
 values=check_inputs(root,output,True)
 before=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(before,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
 b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys() or aa!=bb or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Packed argument descriptor changed another linked body or address')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Packed argument descriptor protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,
  target_words=57,reachable_words=57,frame=96,alignment_words=3,slot_words=60,
  strict_first_link_reproduced=True,guards=0,direct_C_match=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n')
 return result
