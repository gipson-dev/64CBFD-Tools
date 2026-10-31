"""Attached random effect: direct semantic C and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_150B5950','generated_E2DA0'
ENTRY,ROM,BODY,SIZE=0x150B5950,0xE2E00,236,236
SOURCE='conker/src/game/generated_E2DA0.c'
OBJECT='conker/build/src/game/generated_E2DA0.c.o'
ASM='conker/asm/E2DA0.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-attached-random-effect-150B5950-match'
RODATA_SYMBOL=None
RAW_SHA='9b3692c984a046513ce283b43ba1dfb37875e963cef283fc93bda528557545fc'
SNAPSHOT_SHA='ffac937ca2dea2ffd5b881d60d8233a79e362807b39b2645f64f2a517c447e59'
BEFORE_ELF_SHA='b8bdfa1266b65b7c09471ca5606a00d4461ecd29093e099ca39ec7ef6c6d5a8f'
TRUTH_SHA='3509bb99130da58ef1348184bdcfa38930909789698ff6a11629b5e26c63268c'
BINDINGS={72: [('R_MIPS_26', 'func_150ADA68')], 80: [('R_MIPS_HI16', 'D_8009FC98')], 84: [('R_MIPS_LO16', 'D_8009FC98')], 144: [('R_MIPS_26', 'func_150B5A3C')], 156: [('R_MIPS_26', 'func_150ADA68')], 164: [('R_MIPS_HI16', 'D_8009FC9C')], 168: [('R_MIPS_LO16', 'D_8009FC9C')], 192: [('R_MIPS_26', 'func_150B60E0')], 208: [('R_MIPS_26', 'func_150B5A3C')]}
ORIGINAL_BINDINGS={72: [('R_MIPS_26', 'func_150ADA68')], 80: [('R_MIPS_HI16', 'D_8009FC98')], 84: [('R_MIPS_LO16', 'D_8009FC98')], 144: [('R_MIPS_26', 'func_150B5A3C')], 156: [('R_MIPS_26', 'func_150ADA68')], 164: [('R_MIPS_HI16', 'D_8009FC9C')], 168: [('R_MIPS_LO16', 'D_8009FC9C')], 192: [('R_MIPS_26', 'func_150B60E0')], 208: [('R_MIPS_26', 'func_150B5A3C')]}
HEADERS='#include <ultra64.h>\nextern f32 D_8009FC98, D_8009FC9C;\nf32 func_150ADA68(void);\ns32 func_150B5A3C();\nvoid func_150B60E0(u8 *actor, f32 *output);\n'
DECLARATIONS=''
SELECTED='/* Expire a stale attachment or submit the two independently sampled effects. */\nvoid func_150B5950(u8 *record) {\n    f32 sample;\n    f32 position[3];\n    u8 *actor = *(u8 **)(record + 0x28);\n    if (*(s32 *)actor == 0 || record[0x2C] != actor[0x3B]) {\n        *(s16 *)(record + 0xE) = -1;\n    } else if (*(s32 *)(actor + 0x1D4) != 0) {\n        sample = func_150ADA68();\n        if (sample < D_8009FC98) {\n            position[0] = *(f32 *)(actor + 0x14);\n            position[1] = *(f32 *)(actor + 0x18);\n            position[2] = *(f32 *)(actor + 0x1C);\n            func_150B5A3C(position, record[0xC], record[1]);\n        }\n        sample = func_150ADA68();\n        if (sample < D_8009FC9C) {\n            func_150B60E0(actor, position);\n            func_150B5A3C(position, record[0xC], record[1]);\n        }\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected attached-effect owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=236 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Attached random effect body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    a,b=function_span(before,FUNCTION)
    if before[a:b]!='s32 func_150B5950() {\n    return 0;\n}':raise ValueError('Attached-effect placeholder changed')
    declarations=HEADERS.replace('#include <ultra64.h>\n','',1).replace('#include "structs.h"\n','',1)
    after=before[:a]+declarations+SELECTED.rstrip()+before[b:]
    if after.count('void func_150B60E0(u8 *arg0, s32 arg1)')!=1:raise ValueError('Expected position provider definition')
    return after.replace('void func_150B60E0(u8 *arg0, s32 arg1)','void func_150B60E0(u8 *arg0, f32 *arg1)')


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Attached random effect snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Attached random effect frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Attached random effect predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Attached random effect live input differs: '+name)
    return values

METADATA_GROUPS=((0x2C1894,('D_8009FC98','D_800A8F98'),(1,0)),(0x2DE7B4,('D_8009FC9C','D_800A8F9C'),(1,0)))
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Attached random effect named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Attached random effect symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Attached random effect metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Attached random effect frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Attached random effect original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Attached random effect strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Attached random effect named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
 if sha(before)!=GUARD_SHA:raise ValueError('Inherited guard manifest changed')
 return before

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Attached random effect scope changed')
 return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_150B5950.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_E2DA0.c.o', 'make-shadow/src/game/generated_E2DA0.c.o.compact', 'make-shadow/src/game/generated_E2DA0.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Attached random effect artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Attached random effect artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Attached random effect raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Attached random effect evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Attached random effect Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_E2DA0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Attached random effect Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Attached random effect private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Attached random effect changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Attached random effect protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=59,reachable_words=58,frame=56,alignment_words=0,slot_words=59,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='0e1dcd21b2871b8c63c7e128de0c89befa9870d68748dbb979f048976a5728e9'
