"""Effect motion limit: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_150B36AC','generated_DFBF0'
ENTRY,ROM,BODY,SIZE=0x150B36AC,0xE0B5C,224,224
SOURCE='conker/src/game/generated_DFBF0.c'
OBJECT='conker/build/src/game/generated_DFBF0.c.o'
ASM='conker/asm/DFBF0.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-effect-motion-limit-150B36AC-match'
RODATA_SYMBOL=None
RAW_SHA='dd3bc82f1321192dc45e6bb4ca5c54eb8a5e669890fd42c3935d612765e1738f'
SNAPSHOT_SHA='0029f4793ec6307736f17c95ecae87d22014a5b17e6ac32182ab20c9c91320a1'
BEFORE_ELF_SHA='72d17139b031fde8cc28703303696819946ee00a09fa0ed38e021ea44e44f0f3'
TRUTH_SHA='dd3bc82f1321192dc45e6bb4ca5c54eb8a5e669890fd42c3935d612765e1738f'
BINDINGS={}
ORIGINAL_BINDINGS={}
HEADERS='#include <ultra64.h>\n'
DECLARATIONS=''
SELECTED='/* Reset motion above the threshold; otherwise scale its six components. */\ns32 func_150B36AC(u8 *record, s32 unused1, s32 unused2, s32 unused3, f32 offset, void *unused6) {\n    f32 vertical = *(f32 *)(record + 0x48);\n    f32 scale;\n    (void)unused1;\n    (void)unused2;\n    (void)unused3;\n    (void)unused6;\n\n    *(f32 *)(record + 0x3C) = *(f32 *)(record + 0x10) + offset;\n    if (*(f32 *)(record + 0x170) < vertical) {\n        *(u32 *)(record + 0x60) = *(u32 *)(record + 0x60) & ~7u;\n        *(u32 *)(record + 0x60) = *(u32 *)(record + 0x60) & ~8u;\n        *(u32 *)(record + 0x60) = *(u32 *)(record + 0x60) & ~0x40u;\n        *(u32 *)(record + 0x60) = *(u32 *)(record + 0x60) & ~0x20u;\n        *(f32 *)(record + 0x44) = 0.0f;\n        *(f32 *)(record + 0x48) = 0.0f;\n        *(f32 *)(record + 0x4C) = 0.0f;\n        if (*(s16 *)(record + 0x64) >= 33) {\n            *(s16 *)(record + 0x64) = 32;\n        }\n    } else {\n        scale = *(f32 *)(record + 0x14);\n        *(f32 *)(record + 0x44) *= scale;\n        *(f32 *)(record + 0x48) = -vertical * scale;\n        *(f32 *)(record + 0x4C) *= scale;\n        *(f32 *)(record + 0x50) *= scale;\n        *(f32 *)(record + 0x54) *= scale;\n        *(f32 *)(record + 0x58) *= scale;\n    }\n    return 1;\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected effect motion limit diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=224 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Effect motion limit body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_150B36AC() {\n    return 0;\n}':raise ValueError('Effect motion placeholder changed')
    return before[:start]+DECLARATIONS+SELECTED.rstrip()+before[end:]


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Effect motion limit snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Effect motion limit frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Effect motion limit predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Effect motion limit live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Effect motion limit named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Effect motion limit symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Effect motion limit metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Effect motion limit frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Effect motion limit original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Effect motion limit strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Effect motion limit named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
 if sha(before)!=GUARD_SHA or NEW_GUARDS:raise ValueError('Effect motion guard history changed')
 return before

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Effect motion scope changed')
 return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_150B36AC.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_DFBF0.c.o', 'make-shadow/src/game/generated_DFBF0.c.o.compact', 'make-shadow/src/game/generated_DFBF0.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Effect motion limit artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Effect motion limit artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Effect motion limit raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Effect motion limit evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Effect motion limit Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_DFBF0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Effect motion limit Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Effect motion limit private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Effect motion limit changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Effect motion limit protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=56,reachable_words=56,frame=0,alignment_words=0,slot_words=56,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='7ff7e838acb8d1fab239942e8ec9567820b8b35f642e394cb153ccfd4f5ef836'
