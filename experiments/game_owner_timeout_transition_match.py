"""Owner timeout transition: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_1519E754','generated_1CA420'
ENTRY,ROM,BODY,SIZE=0x1519E754,0x1CBC04,196,196
SOURCE='conker/src/game/generated_1CA420.c'
OBJECT='conker/build/src/game/generated_1CA420.c.o'
ASM='conker/asm/1CA420.s'
BUILD='conker/build/game-owner-timeout-transition-match'
RODATA_SYMBOL=None
RAW_SHA="b4c2dc25b7aa7166c5b5c8c65eca4d9d46a7d39f228b3e316086355add54a788"
SNAPSHOT_SHA="a4d726bfff9c25dd3074937da1eb3e77a59dc2a81bbd80128f49eb0a3a985f49"
BEFORE_ELF_SHA="157166a0b932851d5e72143dbf25f4aa78299dd941aaa98a556aa5fbefe5008b"
TRUTH_SHA="495b7c7d68d2644029335f491970507d22ef9f5ae7ff96c5802aa93b22d6ced0"
PARENT,TABLE,TICKS,SLOT,HELPER,FREE=0x15149264,0x8008A4E8,0x800BE9E4,0x800E0920,0x1519E3BC,0x1516972C
BINDINGS={32:[('R_MIPS_HI16','D_800BE9E4')],84:[('R_MIPS_LO16','D_800BE9E4')],132:[('R_MIPS_26','func_1519E3BC')],148:[('R_MIPS_HI16','D_800E0920')],152:[('R_MIPS_LO16','D_800E0920')]}
HEADERS="#include <ultra64.h>\n\n"
DECLARATIONS="extern s32 D_800BE9E4;\nextern u8 *D_800E0920;\nvoid func_1519E3BC(u8 *, s16, u8, s32);\n\n"
SELECTED="/* Retire an invalid owner link or transition it after the timed state ends. */\ntypedef struct {\n    u8 *owner;\n    u8 identity;\n    u8 reserved5[3];\n    s32 elapsed;\n} OwnerTimeoutPayload1CA420;\n\nvoid func_1519E754(u8 *record) {\n    OwnerTimeoutPayload1CA420 *payload = (OwnerTimeoutPayload1CA420 *)(record + 0x28);\n    u8 retire = 0;\n\n    if (*(s32 *)payload->owner == 0) {\n        retire = 1;\n    }\n    if (payload->identity != payload->owner[0x3B]) {\n        retire = 1;\n    }\n    if (retire == 0) {\n        payload->elapsed = (s32)((u32)payload->elapsed + (u32)D_800BE9E4);\n        if (*(u16 *)(payload->owner + 0x84) != 0x7C) {\n            retire = 1;\n            if (payload->elapsed > 200) {\n                func_1519E3BC(payload->owner, 300, record[0xC], record[1]);\n            }\n        }\n    }\n    if (retire != 0) {\n        D_800E0920 = NULL;\n        *(s16 *)(record + 0xE) = -1;\n        record[0xD] |= 1;\n    }\n}"

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected threshold owner diagnostics')
    return 0

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=196 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Owner timeout transition body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_1519E754() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Owner timeout transition placeholder changed')
    return before.replace(stub,SELECTED,1).replace('extern u8 *D_800E0920;', 'extern u8 *D_800E0920;\nextern s32 D_800BE9E4;',1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Owner timeout transition snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Owner timeout transition frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Owner timeout transition predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Owner timeout transition live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Owner timeout transition strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Owner timeout transition original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Owner timeout transition image differs from body and extent prediction')
    expected=Counter((n,f[1],196 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Owner timeout transition named ELF definitions changed')

NEW_GUARDS=[]
def guard_manifest(before):
    if sha(before)!='c9f2d82d72afcd7be14278dbc076ff6b8aa1330ca0f42e11d3bcf51b76923225':raise ValueError('Inherited guard bytes changed')
    return before
def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_1519E754.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game/generated_1CA420.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_1CA420.c.o","make-shadow/src/game/generated_1CA420.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Owner timeout transition artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner timeout transition artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner timeout transition raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Owner timeout transition evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner timeout transition Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1CA420.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Owner timeout transition Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Owner timeout transition private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Owner timeout transition changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner timeout transition protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=49,frame=40,alignment_words=0,slot_words=49,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
