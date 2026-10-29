"""Record position command: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
import sys
from tools import pad_generated_object
sys.modules.setdefault("pad_generated_object",pad_generated_object)
from tools import pad_c_object
def emit_padded_assembly(obj,asm,word_patches_path=None,filename='game_CB1C0',rodata_symbol=None):
    return pad_c_object.emit_padded_assembly(obj,Path(asm).parents[3]/'retail_layout.us.txt',filename,word_patches_path=word_patches_path,rodata_symbol=rodata_symbol)
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1509DDFC','game_CB1C0'
ENTRY,ROM,BODY,SIZE=0x1509DDFC,0xCB2AC,200,200
SOURCE='conker/src/game_CB1C0.c'
OBJECT='conker/build/src/game_CB1C0.c.o'
ASM='conker/asm/nonmatchings/game_CB1C0/func_1509DDFC.s'
BUILD='conker/build/game-record-position-command-match'
RODATA_SYMBOL=None
RAW_SHA='2d0c9c20bae4b47e37a701cdc4903775ae3647f2d82956d11bd1b87333adaeeb'
SNAPSHOT_SHA='c64d1bbca0b652f07cf31394d1be17d757fde8a414319e327f035ceae8e32749'
BEFORE_ELF_SHA='d22097c62aa0d5fd7dc7a9a09af298bb794df92bfb181119ea4f6d5f3ad357c6'
TRUTH_SHA='f4480888046652b0fdc74d42053b610e56ce5833507409308676982ae4a59346'
RESOLVE,ATTACH,POSITION=0x15084000,0x15178BE4,0x15178C34
BINDINGS={56: [('R_MIPS_26', 'func_15084000')], 104: [('R_MIPS_HI16', 'D_800CC2D0')], 108: [('R_MIPS_LO16', 'D_800CC2D0')], 124: [('R_MIPS_26', 'func_15178BE4')], 164: [('R_MIPS_26', 'func_15178C34')]}
HEADERS='#include <ultra64.h>\n#include "functions.h"\n#include "variables.h"\ns32 func_15084000(s32);\nvoid func_15178C34(u8, s32, s32, s32, s16);\nvoid func_15178BE4(u8, f32 *, s16);\n\n'
DECLARATIONS=''
SELECTED='/* Position the selected record using an actor reference or explicit coordinates.\n * Preserve the record ID home across the actor resolver and conditional dispatch. */\ns32 func_1509DDFC(volatile s32 recordId, s32 mode, struct215 *command) {\n    s32 objectIndex;\n\n    switch (mode) {\n        case 0:\n            objectIndex = func_15084000(command->unk8 & ~0x2000);\n            func_15178BE4(recordId & 0xFF,\n                &D_800CC2D0[objectIndex].x_position,\n                command->unkC.s.unk2);\n            return 1;\n        case 1:\n            func_15178C34(recordId & 0xFF, command->unk8, command->unkC.i.unk0,\n                command->unk10, command->unk14);\n            return 1;\n        default:\n            return 0;\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected record-position-command owner diagnostics')
    return 0

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=200 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Record position command body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start=before.index('/* Non-matching C placeholders for asm/nonmatchings/game_CB1C0/func_1509DDFC.s. */');end=before.index('s32 func_1509DEC4(',start)
    if before[start:end].count('s32 func_1509DDFC() {\n    return 0;\n}')!=1:raise ValueError('Record position placeholder changed')
    after=before[:start]+SELECTED+'\n'+before[end:]
    return after.replace('/* Generated placeholder declarations. */\ns32 func_1509DDFC();\n/* End generated placeholder declarations. */\n\n','')

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Record position command snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Record position command frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Record position command predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Record position command live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Record position command strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    named={}
    for pos,name,fields,_ in symbol_rows(before):named.setdefault(name,[]).append((pos,fields))
    rows=named[FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Record position command original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Record position command image differs from body and extent prediction')
    expected=Counter((n,f[1],200 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Record position command named ELF definitions changed')

NEW_GUARDS=[]
def guard_manifest(before):
    if sha(before)!='efd6bd3f1e7efba51b4b566abfd447477133a8a52daa3804bc7550b32d273293':raise ValueError('Inherited guard bytes changed')
    return before
def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_1509DDFC.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game_CB1C0.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game_CB1C0.c.o","make-shadow/src/game_CB1C0.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Record position command artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record position command artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record position command raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Record position command evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record position command Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game_CB1C0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Record position command Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Record position command private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Record position command changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Record position command protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=50,frame=40,alignment_words=0,slot_words=50,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
