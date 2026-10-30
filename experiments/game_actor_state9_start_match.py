"""Actor state-9 start: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_15063404','generated_90840'
ENTRY,ROM,BODY,SIZE=0x15063404,0x908B4,224,224
SOURCE='conker/src/game/generated_90840.c'
OBJECT='conker/build/src/game/generated_90840.c.o'
ASM='conker/asm/90840.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-actor-state9-start-15063404-match'
RODATA_SYMBOL=None
RAW_SHA='8c9148fea143299e9a1b052eb4bfc2004d0a9003379b1b8205777ed0ce579d67'
SNAPSHOT_SHA='ee601f44981ec129f0652ff5435d75e49141cb3f35142d883d7b4d96621cbe4a'
BEFORE_ELF_SHA='1952d0caf95c252112f271bbd523a87d345ba216c81ef9a1dcd5849bb7c236b1'
TRUTH_SHA='ff370fa8491731248a834409305133d40b5e8db49e1aa7b5970577dd5adfb28b'
BINDINGS={4: [('R_MIPS_HI16', 'D_800CC2D0')], 8: [('R_MIPS_LO16', 'D_800CC2D0')], 100: [('R_MIPS_26', 'func_15083568')], 120: [('R_MIPS_26', 'func_15083568')], 200: [('R_MIPS_26', 'func_1505E650')]}
ORIGINAL_BINDINGS={4: [('R_MIPS_HI16', 'D_800CC2D0')], 8: [('R_MIPS_LO16', 'D_800CC2D0')], 100: [('R_MIPS_26', 'func_15083568')], 120: [('R_MIPS_26', 'func_15083568')], 200: [('R_MIPS_26', 'func_1505E650')]}
HEADERS='#include <ultra64.h>\n#include "structs.h"\nextern struct127 D_800CC2D0[];\nu8 *func_15083568(u8 *, s32, f32, s32);\nvoid func_1505E650(u8 *, u16, f32, f32, f32, f32, s32);\n\n'
DECLARATIONS=''
SELECTED='/* Set nested state 9, start requests 0x1D/0x1E, and reset its counters. */\nvoid func_15063404(struct127 *actor) {\n    struct127 *entry = &D_800CC2D0[(u32)(((s32)actor -\n        (s32)D_800CC2D0) / (s32)sizeof(struct127))];\n\n    entry->unk31C->unk78 = 9;\n    func_15083568((u8 *)actor, 0x1D, 1.0f, 0);\n    func_15083568((u8 *)actor, 0x1E, 1.0f, 0);\n    actor->disable_jump = 20;\n    actor->disable_run = 0;\n    actor->unk83 = 0;\n    *(s16 *)((u8 *)entry->unk31C + 0x24) = 60;\n    entry->unk31C->unk11A = 2;\n    func_1505E650((u8 *)actor, 0x7F, 1.0f, 0.0f, 0.0f, 0.0f, 0);\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected actor state-9 start diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=224 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Actor state-9 start body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_15063404() {\n    return 0;\n}':raise ValueError('Actor state-9 placeholder changed')
    return before[:start]+DECLARATIONS+SELECTED.rstrip()+before[end:]


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Actor state-9 start snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Actor state-9 start frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Actor state-9 start predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Actor state-9 start live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Actor state-9 start named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Actor state-9 start symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Actor state-9 start metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Actor state-9 start frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Actor state-9 start original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Actor state-9 start strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Actor state-9 start named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
 if sha(before)!=GUARD_SHA or NEW_GUARDS:raise ValueError('Actor state-9 guard history changed')
 return before

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Actor state-9 scope changed')
 return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_15063404.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_90840.c.o', 'make-shadow/src/game/generated_90840.c.o.compact', 'make-shadow/src/game/generated_90840.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Actor state-9 start artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor state-9 start artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor state-9 start raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Actor state-9 start evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor state-9 start Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_90840.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Actor state-9 start Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Actor state-9 start private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Actor state-9 start changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Actor state-9 start protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=56,reachable_words=56,frame=48,alignment_words=0,slot_words=56,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='0d1b6200117db2da46587d9776ac0a8e1c7701849dd2020c6b21a92ffae6637b'
