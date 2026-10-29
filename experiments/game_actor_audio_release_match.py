"""Actor audio release: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_150E3514','generated_1104D0'
ENTRY,ROM,BODY,SIZE=0x150E3514,0x1109C4,200,200
SOURCE='conker/src/game/generated_1104D0.c'
OBJECT='conker/build/src/game/generated_1104D0.c.o'
ASM='conker/asm/1104D0.s'
BUILD='conker/build/game-actor-audio-release-match'
RODATA_SYMBOL=None
RAW_SHA='8473beb18225c534c22b59530919bb225382746333417e64102f9129fe005951'
SNAPSHOT_SHA='e993c8b3678aadc5c169c6afaf1f27ec94ee58331c94a2b6e076333ed5e86e45'
BEFORE_ELF_SHA='8d8dbb6c26161c75fa60e44f36576aaae96e55644f836b81fb5e41bd8feecb22'
TRUTH_SHA='ea6cf608bed9ea5cc1d55a6cbc8b5d24bd57e4876bcc7b3435c5623445775dfb'
TABLE,STOP,AUDIO,RELEASE=0x800D99D0,0x100111C8,0x10010F88,0x1516972C
BINDINGS={20: [('R_MIPS_HI16', 'D_800D99D0')], 24: [('R_MIPS_LO16', 'D_800D99D0')], 68: [('R_MIPS_26', 'func_100111C8')], 164: [('R_MIPS_26', 'func_10010F88')], 172: [('R_MIPS_26', 'func_1516972C')]}
HEADERS='#include <ultra64.h>\n#include "structs.h"\ntypedef struct { u8 type; u8 pad1[0xF]; f32 x, y, z; } Generated1104D0Actor;\nextern Generated1104D0Actor *D_800D99D0[8];\nvoid func_100111C8(u16 handle);\nu16 func_10010F88(s32, u16, s16, u8, s32, s16, s16, s16, s16, s16);\nvoid func_1516972C(struct102 *actor);\n\n'
DECLARATIONS='void func_100111C8(u16 handle);\nu16 func_10010F88(s32, u16, s16, u8, s32, s16, s16, s16, s16, s16);\nvoid func_1516972C(struct102 *actor);\n\n'
SELECTED='/* Clear the matching actor slot, replace an active sound, then release the actor. */\nvoid func_150E3514(u8 *actor) {\n    s32 slot;\n    slot = *(u8 *)(actor + 0x48);\n    if (slot >= 0 && (u8 *)D_800D99D0[slot] == actor) {\n        D_800D99D0[slot] = NULL;\n    }\n    if (*(u16 *)(actor + 0x4A) != 0) {\n        func_100111C8(*(u16 *)(actor + 0x4A));\n        *(u16 *)(actor + 0x4A) = 0;\n        func_10010F88(0x2D7, 0x5DC0, 0, 0, 0,\n                     (s32)*(f32 *)(actor + 0x28),\n                     (s32)*(f32 *)(actor + 0x2C),\n                     (s32)*(f32 *)(actor + 0x30), 1000, 6000);\n    }\n    func_1516972C((struct102 *)actor);\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected actor-audio-release owner diagnostics')
    return 0

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=200 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Actor audio release body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_150E3514() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1 or before.count('#include <ultra64.h>')!=1:raise ValueError('Actor audio release placeholder/header changed')
    if '#include "structs.h"' in before:raise ValueError('Actor audio release owner already includes structs')
    return before.replace('#include <ultra64.h>','#include <ultra64.h>'+chr(10)+'#include "structs.h"',1).replace(stub,(DECLARATIONS+SELECTED).strip(),1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Actor audio release snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Actor audio release frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Actor audio release predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Actor audio release live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Actor audio release strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    named={}
    for pos,name,fields,_ in symbol_rows(before):named.setdefault(name,[]).append((pos,fields))
    rows=named[FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Actor audio release original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Actor audio release image differs from body and extent prediction')
    expected=Counter((n,f[1],200 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Actor audio release named ELF definitions changed')

NEW_GUARDS=[]
def guard_manifest(before):
    if sha(before)!='efd6bd3f1e7efba51b4b566abfd447477133a8a52daa3804bc7550b32d273293':raise ValueError('Inherited guard bytes changed')
    return before
def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_150E3514.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game/generated_1104D0.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_1104D0.c.o","make-shadow/src/game/generated_1104D0.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Actor audio release artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor audio release artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor audio release raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Actor audio release evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor audio release Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1104D0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Actor audio release Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Actor audio release private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Actor audio release changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Actor audio release protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=50,frame=56,alignment_words=0,slot_words=50,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
