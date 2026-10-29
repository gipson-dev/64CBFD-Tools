"""State byte publisher: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_151738C4','generated_1A0790'
ENTRY,ROM,BODY,SIZE=0x151738C4,0x1A0D74,208,208
SOURCE='conker/src/game/generated_1A0790.c'
OBJECT='conker/build/src/game/generated_1A0790.c.o'
ASM='conker/asm/1A0790.s'
BUILD='conker/build/game-state-byte-publisher-match'
RODATA_SYMBOL=None
PROVIDER=0x151733E4
RAW_SHA='840d3103fe77315fbd403eea1bc7c7e95ffdb78129391d210e3cb3b2a1584c69'
SNAPSHOT_SHA='1d24fbd5d144d48fdb51f0d5237b970e5c7293c32730dc100ddef2764626644e'
BEFORE_ELF_SHA='199b50f0b01713d4d7a472cb13aed15a40e8cf24eb8ae1630abd25d8bd2278ed'
TRUTH_SHA='af5b7c47f392eebbd00133f95bd8f3afc2396a098cddd897fa7bd1576e9e5d7f'
BINDINGS={12: [('R_MIPS_HI16', 'D_800B0DF0')], 16: [('R_MIPS_LO16', 'D_800B0DF0')], 24: [('R_MIPS_HI16', 'D_800DBFF0')], 40: [('R_MIPS_LO16', 'D_800DBFF0')], 76: [('R_MIPS_26', 'func_151733E4')], 84: [('R_MIPS_HI16', 'D_800DD2E4')], 88: [('R_MIPS_LO16', 'D_800DD2E4')], 92: [('R_MIPS_HI16', 'D_800DBEA8')], 108: [('R_MIPS_LO16', 'D_800DBEA8')], 144: [('R_MIPS_26', 'func_151733E4')], 160: [('R_MIPS_HI16', 'D_800DBEA8')], 164: [('R_MIPS_LO16', 'D_800DBEA8')], 152: [('R_MIPS_HI16', 'D_800B0DF0')], 156: [('R_MIPS_LO16', 'D_800B0DF0')]}
HEADERS='#include <ultra64.h>\ntypedef struct {\n    u8 pad[0x46];\n    s8 value;\n} Generated1A0790State;\nextern Generated1A0790State *D_800B0DF0;\nextern u8 *D_800DBFF0;\nextern u8 D_800DD2E4[], D_800DBEA8[];\n/* Retail consumes five 32-bit arguments; the provider C body remains a placeholder. */\ns32 func_151733E4();\n'
DECLARATIONS='extern u8 *D_800DBFF0;\nextern u8 D_800DD2E4[], D_800DBEA8[];\n/* Retail consumes five 32-bit arguments; the provider C body remains a placeholder. */\ns32 func_151733E4();\n'
SELECTED='/* Publish the selected three-byte state after updating its provider. */\nvoid func_151738C4(s32 context) {\n    u8 *state;\n\n    if (D_800B0DF0->value == -1) {\n        if (*(u32 *)(D_800DBFF0 + 0x5F0) & 1) {\n            func_151733E4(6, 6, context, 0, -1);\n            D_800DBEA8[0] = D_800DD2E4[0];\n            D_800DBEA8[1] = D_800DD2E4[1];\n            D_800DBEA8[2] = D_800DD2E4[2];\n        } else {\n            func_151733E4(0, 0, context, 0, -1);\n            state = (u8 *)D_800B0DF0;\n            D_800DBEA8[0] = state[5];\n            D_800DBEA8[1] = state[6];\n            D_800DBEA8[2] = state[7];\n        }\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected State byte publisher owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=208 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('State byte publisher body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_151738C4() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('State byte publisher placeholder changed')
    return before.replace(stub,DECLARATIONS+SELECTED.strip(),1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('State byte publisher snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('State byte publisher frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('State byte publisher predecessor changed')
    return values

OTHER_SOURCE='conker/src/game_45B80.c'
OTHER_OBJECT='conker/build/src/game_45B80.c.o'
def recovered_caller(before):
    old='s32 func_151738C4(s32);'
    if before.count(old)!=1:raise ValueError('Publisher caller changed')
    return before.replace(old,'void func_151738C4(s32);',1)

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    if installed:changes[OTHER_SOURCE]=recovered_caller(values[OTHER_SOURCE].decode()).encode()
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('State byte publisher live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('State byte publisher frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('State byte publisher original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('State byte publisher strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('State byte publisher named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
    if sha(before)!='84c233dfd374f8ba8b4f66dca69b180bc2b8b3813b7a1a594d72f88130ba0306':raise ValueError('State byte publisher inherited guards changed')
    return before

def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)


ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_151738C4.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-best-input.c","make-shadow/src/game/generated_1A0790.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_1A0790.c.o","make-shadow/src/game/generated_1A0790.c.o.padded.s",)

EVIDENCE=EVIDENCE+('proposed-caller.c', 'caller-declaration-proof.json', 'caller-before.o', 'caller-after.o', 'caller-make-shadow/src/game_45B80.c.o', 'caller-actual-Make-plan.txt', 'before-owner-nodebug.c', 'before-owner-nodebug-processed.c', 'before-owner-nodebug.o', 'before-owner-nodebug-diagnostics.txt', 'after-owner-nodebug.c', 'after-owner-nodebug-processed.c', 'after-owner-nodebug.o', 'after-owner-nodebug-diagnostics.txt')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('State byte publisher artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('State byte publisher artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('State byte publisher raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('State byte publisher evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('State byte publisher Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1A0790.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('State byte publisher Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('State byte publisher private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('State byte publisher changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('State byte publisher protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=52,frame=32,alignment_words=0,slot_words=52,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
