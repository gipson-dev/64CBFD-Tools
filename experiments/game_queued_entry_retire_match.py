"""Queued entry retire: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_1518AA10','generated_1B7EC0'
ENTRY,ROM,BODY,SIZE=0x1518AA10,0x1B7EC0,204,204
SOURCE='conker/src/game/generated_1B7EC0.c'
OBJECT='conker/build/src/game/generated_1B7EC0.c.o'
ASM='conker/asm/1B7EC0.s'
BUILD='conker/build/game-queued-entry-retire-match'
RODATA_SYMBOL=None
RAW_SHA='2287698d953c6a0466f6abd993e012818c9e132b086027a012312bcce62127be'
SNAPSHOT_SHA='5c8d37df192f7c22217fb823ea9249383a4b94fcee97db39baf7fb3aeafe998b'
BEFORE_ELF_SHA='012521835d1ec8992937f707b4ff2fdfbb3bb9356d573383dff222b0f2ec3143'
TRUTH_SHA='8e46509dd03b21a98974976efb2b1f45680ef845d6af2d7fa22e8ac987238350'
BINDINGS={40: [('R_MIPS_HI16', 'D_8008D5C0')], 96: [('R_MIPS_LO16', 'D_8008D5C0')], 128: [('R_MIPS_26', 'func_1516972C')], 160: [('R_MIPS_HI16', 'D_800BE9E4')], 176: [('R_MIPS_LO16', 'D_800BE9E4')]}
HEADERS='#include <ultra64.h>\n#include "structs.h"\nextern s32 D_800BE9E4;\nextern void (*D_8008D5C0[])(u8 *);\nvoid func_1516972C(struct102 *);\n\n'
DECLARATIONS='#include "structs.h"\nextern s32 D_800BE9E4;\nextern void (*D_8008D5C0[])(u8 *);\nvoid func_1516972C(struct102 *);\n\n'
SELECTED='/* Retire the queued entry after expiry, or advance the enabled timer. */\nvoid func_1518AA10(u8 *queue) {\n    u8 *next;\n    u8 *entry;\n\n    if (*(u32 *)(queue + 0x1C) != 0) {\n        if (*(s16 *)(queue + 0x22) < 0) {\n            entry = *(u8 **)(queue + 0x14);\n            next = *(u8 **)(entry + 0x18);\n            if (next == NULL) {\n                *(s32 *)(queue + 0x10) = 0;\n                *(s32 *)(queue + 0x14) = 0;\n            } else {\n                /* Reload the link after clearing next: the fields may alias. */\n                *(s32 *)(next + 0x14) = 0;\n                *(u8 **)(queue + 0x14) = *(u8 **)(entry + 0x18);\n            }\n            if (entry[0x1C] != 0) {\n                D_8008D5C0[entry[0x1C]](*(u8 **)(entry + 0x10));\n            }\n            func_1516972C((struct102 *)entry);\n            /* Release callbacks can change the count before this decrement. */\n            *(u32 *)(queue + 0x1C) -= 1;\n        } else if (queue[0x24] & 1) {\n            *(s16 *)(queue + 0x22) = (u32)*(s16 *)(queue + 0x22) - (u32)D_800BE9E4;\n        }\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected queued-entry owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=204 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Queued entry retire body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_1518AA10() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Queued entry retire placeholder changed')
    return before.replace('#include <ultra64.h>\n','#include <ultra64.h>\n\n'+DECLARATIONS,1).replace(stub,SELECTED.strip())


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Queued entry retire snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Queued entry retire frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Queued entry retire predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Queued entry retire live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Queued entry retire frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Queued entry retire original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    # Two closed GNU symbol/string bucket swaps; preserve every definition.
    named={n:(p,f,loc)for p,n,f,loc in symbol_rows(before)}
    for names,position,location,nameoff in ((('D_80099804','D_8009EE54'),2827092,3102260,87680),(('D_8008D5C0','D_80088820'),2856196,3125818,111238)):
        rows=[named[n]for n in names]
        for i,(name,(p,f,loc))in enumerate(zip(names,rows)):
            if(p,loc)!=(position+16*i,location+11*i)or f!=(nameoff+11*i,int(name[2:],16),0,16,0,6 if name=='D_8009EE54'else 65521)or before[loc:loc+11]!=name.encode()+b'\0':raise ValueError('Queued-entry symbol bucket changed: '+name)
        for dest,origin,name in((rows[0],rows[1],names[1]),(rows[1],rows[0],names[0])):
            struct.pack_into('>IIIBBH',result,dest[0],dest[1][0],*origin[1][1:]);result[dest[2]:dest[2]+11]=name.encode()+b'\0'
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Queued entry retire strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Queued entry retire named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
    if sha(before)!='1e58e8b29313c9ffe2b784379c53af9fdc8eb9152c9bb3d1e1a5fb832a5d26b6':raise ValueError('Queued entry retire inherited guards changed')
    return before

def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)


ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_1518AA10.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-best-input.c","make-shadow/src/game/generated_1B7EC0.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_1B7EC0.c.o","make-shadow/src/game/generated_1B7EC0.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Queued entry retire artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Queued entry retire artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Queued entry retire raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Queued entry retire evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Queued entry retire Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1B7EC0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Queued entry retire Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Queued entry retire private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Queued entry retire changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Queued entry retire protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=51,frame=32,alignment_words=0,slot_words=51,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
