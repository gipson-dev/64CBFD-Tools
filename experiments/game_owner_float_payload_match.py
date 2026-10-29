"""Owner float payload: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_1510A344','generated_1368C0'
ENTRY,ROM,BODY,SIZE=0x1510A344,0x1377F4,200,200
SOURCE='conker/src/game/generated_1368C0.c'
OBJECT='conker/build/src/game/generated_1368C0.c.o'
ASM='conker/asm/1368C0.s'
BUILD='conker/build/game-owner-float-payload-match'
RODATA_SYMBOL=None
RAW_SHA='4a5b8b2816a89997ccbdb96b2ccfb95bf8626f394a38b7dbab2d46bbb0ebcc82'
SNAPSHOT_SHA='24c1d457161bc51a5714947e5b839aaa3ed0abdbfbe8d3ea46526b9847c0cf78'
BEFORE_ELF_SHA='d58ca358aebe9cfdc02775b59e8fb8c705be28ed99b204ad673680e9cd5e5c16'
TRUTH_SHA='dfa842c69b3013af1892d55de2b678a98d85f067bebb2c239ff5e90a18927c2a'
BINDINGS={32: [('R_MIPS_HI16', 'D_800A2684')], 60: [('R_MIPS_LO16', 'D_800A2684')], 64: [('R_MIPS_HI16', 'D_800A2688')], 72: [('R_MIPS_LO16', 'D_800A2688')], 140: [('R_MIPS_26', 'func_15149130')], 168: [('R_MIPS_26', 'memcpy')]}
HEADERS='#include <ultra64.h>\n\ntypedef struct {\n    u8 *owner;\n    u8 ownerId;\n    f32 value0;\n    f32 value1;\n    f32 value2;\n} OwnerFloatPayload;\nextern f32 D_800A2684;\nextern f32 D_800A2688;\nvoid *func_15149130(s16, s8, s8, s8, u8, u8, s32, u8, s32);\nvoid *memcpy(void *, const void *, u32);\n\n'
DECLARATIONS='typedef struct {\n    u8 *owner;\n    u8 ownerId;\n    f32 value0;\n    f32 value1;\n    f32 value2;\n} OwnerFloatPayload;\nextern f32 D_800A2684;\nextern f32 D_800A2688;\nvoid *func_15149130(s16, s8, s8, s8, u8, u8, s32, u8, s32);\nvoid *memcpy(void *, const void *, u32);\n\n'
SELECTED='/* Create an owner-linked payload with three initial float values. */\nvoid *func_1510A344(u8 *owner, s16 lifetime, u8 priority, s32 arg3) {\n    u8 *created;\n    OwnerFloatPayload payload;\n\n    if (owner == NULL) {\n        return NULL;\n    }\n    payload.owner = owner;\n    payload.ownerId = owner[0x3B];\n    payload.value0 = 0.0f;\n    payload.value1 = D_800A2684;\n    payload.value2 = D_800A2688;\n    created = func_15149130(lifetime, -1, 0x1C, -1, 1, 0x1C,\n                           sizeof(payload), priority, arg3);\n    if (created != NULL) {\n        memcpy(created + 0x28, &payload, sizeof(payload));\n    }\n    return created;\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected owner-float-payload owner diagnostics')
    return 0

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=200 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Owner float payload body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_1510A344() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Owner float payload placeholder changed')
    return before.replace(stub,(DECLARATIONS+SELECTED).strip())


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Owner float payload snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Owner float payload frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Owner float payload predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Owner float payload live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Owner float payload strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    named={}
    for pos,name,fields,_ in symbol_rows(before):named.setdefault(name,[]).append((pos,fields))
    rows=named[FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Owner float payload original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Owner float payload image differs from body and extent prediction')
    expected=Counter((n,f[1],200 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Owner float payload named ELF definitions changed')

NEW_GUARDS=[]
def guard_manifest(before):
    if sha(before)!='1678dac601e1def3df3c6438b7a8b4bb0914ce5ef73a929921f12916f7ead9f2':raise ValueError('Inherited guard bytes changed')
    return before
def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_1510A344.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game/generated_1368C0.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_1368C0.c.o","make-shadow/src/game/generated_1368C0.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Owner float payload artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner float payload artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner float payload raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Owner float payload evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner float payload Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1368C0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Owner float payload Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Owner float payload private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Owner float payload changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner float payload protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=50,frame=72,alignment_words=0,slot_words=50,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

FACTORY,COPY=0x15149130,0x10022EC0
