"""Bounce random sound: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_15133C58','generated_15F680'
ENTRY,ROM,BODY,SIZE=0x15133C58,0x161108,200,200
SOURCE='conker/src/game/generated_15F680.c'
OBJECT='conker/build/src/game/generated_15F680.c.o'
ASM='conker/asm/15F680.s'
BUILD='conker/build/game-bounce-random-sound-match'
RODATA_SYMBOL=None
RAW_SHA='8fc58e46f2f4c858c517f624382103243fff0462d90b74a572fa96718838fe09'
SNAPSHOT_SHA='0929e7844e36b1c8e8cf4f5186fb49bda26320ceda0cf9faf9355ff2bfa5fadd'
BEFORE_ELF_SHA='c1bc01a42ee33d3adf16f4340db37d94ba50b44a463dbea05f7b9f0ccb84030d'
TRUTH_SHA='d28ae3d6ca950eae5b05e904035faf01bcbad6e041d3ba7e14df3116b335a16a'
BOUNCE,RANDOM,AUDIO=0x15133B98,0x150ADA20,0x10010F88
BINDINGS={44:[('R_MIPS_26','func_15133B98')],52:[('R_MIPS_26','func_150ADA20')],72:[('R_MIPS_26','func_150ADA20')],172:[('R_MIPS_26','func_10010F88')]}
HEADERS='#include <ultra64.h>\ns32 func_15133B98(u8 *, f32, f32, f32, f32, void *);\ns32 func_150ADA20(void);\nu16 func_10010F88(s32, u16, s16, u8, s32, s16, s16, s16, s16, s16);\n\n'
DECLARATIONS='s32 func_15133B98(u8 *, f32, f32, f32, f32, void *);\ns32 func_150ADA20(void);\nu16 func_10010F88(s32, u16, s16, u8, s32, s16, s16, s16, s16, s16);\n\n'
SELECTED='/* Apply the bounce response, then sometimes play a positional impact sound. */\ns32 func_15133C58(u8 *actor, f32 x, f32 y, f32 z, f32 height, void *contact) {\n    func_15133B98(actor, x, y, z, height, contact);\n    if (func_150ADA20() & 1) {\n        func_10010F88((u32)func_150ADA20() % 9 + 0x2DE,\n                     0x2EE0, 0, 0, 0, (s32)x, (s32)y, (s32)z, 500, 1000);\n    }\n    return 1;\n}\n'

def check_owner_diagnostics(text):
    normalized=re.sub(r'Warning 712: [^,\n]+, line','Warning 712: OWNER, line',text)
    if normalized!='cfe: Warning 712: OWNER, line 96: illegal combination of pointer and integer\n             func_100043B4(arg0->entries[i], 4);\n ---------------------------------------^\ncfe: Warning 712: OWNER, line 100: illegal combination of pointer and integer\n         func_100043B4(arg0->trailing, 4);\n --------------------------^\n':raise ValueError('Unexpected bounce-random-sound owner diagnostics: '+text)
    return 2

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=200 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Bounce random sound body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_15133C58() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Bounce random sound placeholder changed')
    return before.replace(stub,(DECLARATIONS+SELECTED).strip(),1)

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Bounce random sound snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Bounce random sound frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Bounce random sound predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Bounce random sound live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Bounce random sound strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    named={}
    for pos,name,fields,_ in symbol_rows(before):named.setdefault(name,[]).append((pos,fields))
    rows=named[FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Bounce random sound original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Bounce random sound image differs from body and extent prediction')
    expected=Counter((n,f[1],200 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Bounce random sound named ELF definitions changed')

NEW_GUARDS=[]
def guard_manifest(before):
    if sha(before)!='efd6bd3f1e7efba51b4b566abfd447477133a8a52daa3804bc7550b32d273293':raise ValueError('Inherited guard bytes changed')
    return before
def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_15133C58.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game/generated_15F680.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_15F680.c.o","make-shadow/src/game/generated_15F680.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Bounce random sound artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Bounce random sound artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Bounce random sound raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Bounce random sound evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Bounce random sound Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_15F680.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Bounce random sound Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Bounce random sound private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Bounce random sound changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Bounce random sound protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=50,frame=48,alignment_words=0,slot_words=50,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
