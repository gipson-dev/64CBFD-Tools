"""Periodic phase spawn: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_150D2374','generated_FF5C0'
ENTRY,ROM,BODY,SIZE=0x150D2374,0xFF824,212,220
SOURCE='conker/src/game/generated_FF5C0.c'
OBJECT='conker/build/src/game/generated_FF5C0.c.o'
ASM='conker/asm/FF5C0.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-periodic-phase-spawn-match'
RODATA_SYMBOL=None
RAW_SHA='13d015c9169b78d0c99312ab325c49529cc33348d672dfbe924591bdac3aeb1e'
SNAPSHOT_SHA='073d60b31f23fdab581335ae8ad17b64182d6a268fc292f1c7e67930ce23d0fa'
BEFORE_ELF_SHA='7b2e499e2881a0af7aa52401b5535a1bdbf79bb5cc35e7a897142d7d00a58bae'
TRUTH_SHA='fa00b599bb238245cb879751757d4d72ad6f027b1fa00acf4c655b13b2cb84e0'
BINDINGS={16: [('R_MIPS_HI16', 'D_800BE9E4')], 20: [('R_MIPS_LO16', 'D_800BE9E4')], 40: [('R_MIPS_26', 'func_150ADA20')], 132: [('R_MIPS_26', 'func_150D2110')], 140: [('R_MIPS_26', 'func_150ADA20')]}
ORIGINAL_BINDINGS={16: [('R_MIPS_HI16', 'D_800BE9E4')], 20: [('R_MIPS_LO16', 'D_800BE9E4')], 40: [('R_MIPS_26', 'func_150ADA20')], 132: [('R_MIPS_26', 'func_150D2110')], 140: [('R_MIPS_26', 'func_150ADA20')]}
HEADERS='#include <ultra64.h>\nextern s32 D_800BE9E4;\ns32 func_150ADA20(void);\nvoid func_150D2110(s16, f32, f32, u8, u8, u8, s32);\n\ntypedef struct {\n    u32 baseDelay;\n    u32 delayRange;\n    s32 timer;\n    s16 baseLifetime;\n    s16 lifetimeRange;\n    f32 activeDuration;\n    f32 inactiveDuration;\n    u8 activeColor;\n    u8 inactiveColor;\n} PeriodicPhaseSpawnFF5C0;\n\n'
DECLARATIONS='extern s32 D_800BE9E4;\ns32 func_150ADA20(void);\n\ntypedef struct {\n    u32 baseDelay;\n    u32 delayRange;\n    s32 timer;\n    s16 baseLifetime;\n    s16 lifetimeRange;\n    f32 activeDuration;\n    f32 inactiveDuration;\n    u8 activeColor;\n    u8 inactiveColor;\n} PeriodicPhaseSpawnFF5C0;\n\n'
SELECTED='/* Spawn a randomized phase cycle on expiry, then select the next delay. */\nvoid func_150D2374(u8 *owner) {\n    PeriodicPhaseSpawnFF5C0 *state = (PeriodicPhaseSpawnFF5C0 *)(owner + 0x28);\n    u32 random;\n\n    *(s32 *)(owner + 0x30) = (s32)((u32)*(s32 *)(owner + 0x30) - (u32)D_800BE9E4);\n    if (*(s32 *)(owner + 0x30) < 0) {\n        random = (u32)func_150ADA20();\n        func_150D2110((s16)(random % (state->lifetimeRange + 1) + state->baseLifetime),\n                     state->activeDuration, state->inactiveDuration,\n                     state->activeColor, state->inactiveColor, owner[0xC], owner[1]);\n        random = (u32)func_150ADA20();\n        state->timer = (s32)(random % (state->delayRange + 1U) +\n                             state->baseDelay);\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected Periodic phase spawn owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=212 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Periodic phase spawn body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_150D2374() {\n    return 0;\n}':raise ValueError('Periodic phase placeholder changed')
    return before[:start]+DECLARATIONS+SELECTED.rstrip()+before[end:]



def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Periodic phase spawn snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Periodic phase spawn frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Periodic phase spawn predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Periodic phase spawn live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Periodic phase spawn named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Periodic phase spawn symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Periodic phase spawn metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Periodic phase spawn frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Periodic phase spawn original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Periodic phase spawn strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Periodic phase spawn named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
    if sha(before)!='4ad9be793b0ae038d412987b239137e8666dcd4bc2cb79432c22592d53ea7cea':raise ValueError('Inherited guard manifest changed')
    return before





def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)



ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_150D2374.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-best-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_FF5C0.c.o', 'make-shadow/src/game/generated_FF5C0.c.o.compact', 'make-shadow/src/game/generated_FF5C0.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Periodic phase spawn artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Periodic phase spawn artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Periodic phase spawn raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Periodic phase spawn evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Periodic phase spawn Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_FF5C0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Periodic phase spawn Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Periodic phase spawn private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Periodic phase spawn changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Periodic phase spawn protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=53,frame=64,alignment_words=2,slot_words=55,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
