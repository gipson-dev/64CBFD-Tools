"""Payload effect factory: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_150F0198','generated_11C2B0'
ENTRY,ROM,BODY,SIZE=0x150F0198,0x11D648,200,200
SOURCE='conker/src/game/generated_11C2B0.c'
OBJECT='conker/build/src/game/generated_11C2B0.c.o'
ASM='conker/asm/11C2B0.s'
BUILD='conker/build/game-payload-effect-factory-match'
RODATA_SYMBOL=None
RAW_SHA='79543186a84e4093e137a210bd099acea312e832f1a2362924b39b3df61a528d'
SNAPSHOT_SHA='43f46ceea81b3d1583f0243cb2722d270ef7dbfe8481df124575f71d3187682b'
BEFORE_ELF_SHA='e85af7c47fd8491a2d2fb28b8f025e0e5ff48e8bd529756b0476451fdec694ae'
TRUTH_SHA='e9471b777e5c9c1fb7040b83546913ea919a1d7a4c58e82fe1c4cb17c0cb7887'
BINDINGS={140: [('R_MIPS_26', 'func_151602C0')], 168: [('R_MIPS_26', 'memcpy')]}
HEADERS='#include <ultra64.h>\n#include "structs.h"\nstruct225 *func_151602C0(Header *, Header2 *, s32, s32, s32, s32, u8, u8, s32, u8, s32);\nvoid *memcpy(void *, const void *, unsigned int);\n\n'
DECLARATIONS='struct225 *func_151602C0(Header *, Header2 *, s32, s32, s32, s32, u8, u8, s32, u8, s32);\nvoid *memcpy(void *, const void *, u32);\n\n'
SELECTED='/* Create the type-0x21 effect and attach its four-byte owner payload. */\nstruct225 *func_150F0198(u8 arg0, u8 arg1, u8 arg2, u8 arg3, void *owner, u8 arg5, s32 arg6) {\n    struct225 *created;\n    Header header;\n    Header2 position;\n    void *payload;\n\n    payload = owner;\n    header.unk0 = 2;\n    header.unk1 = -1;\n    header.unk2 = 300;\n    header.unk4 = 0x21;\n    position.unk0 = 0;\n    position.unk4 = 0;\n    position.unk8 = 0;\n    created = func_151602C0(&header, &position, arg0, arg1, arg2, arg3, 0xFF, 0, 4, arg5, arg6);\n    if (created != NULL) {\n        memcpy((u8 *)created + 0x18, &payload, 4);\n    }\n    return created;\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected payload-effect-factory owner diagnostics')
    return 0

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=200 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Payload effect factory body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_150F0198() {\n    return 0;\n}'
    declaration='void *memcpy(void *, const void *, u32);\n'
    if before.count(stub)!=1 or before.count(declaration)!=1:raise ValueError('Payload factory placeholder/declaration changed')
    return before.replace(declaration,'').replace(stub,DECLARATIONS+SELECTED.strip())


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Payload effect factory snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Payload effect factory frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Payload effect factory predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Payload effect factory live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Payload effect factory strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    named={}
    for pos,name,fields,_ in symbol_rows(before):named.setdefault(name,[]).append((pos,fields))
    rows=named[FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Payload effect factory original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Payload effect factory image differs from body and extent prediction')
    expected=Counter((n,f[1],200 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Payload effect factory named ELF definitions changed')

NEW_GUARDS=[]
def guard_manifest(before):
    if sha(before)!='1678dac601e1def3df3c6438b7a8b4bb0914ce5ef73a929921f12916f7ead9f2':raise ValueError('Inherited guard bytes changed')
    return before
def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_150F0198.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game/generated_11C2B0.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_11C2B0.c.o","make-shadow/src/game/generated_11C2B0.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Payload effect factory artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Payload effect factory artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Payload effect factory raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Payload effect factory evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Payload effect factory Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_11C2B0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Payload effect factory Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Payload effect factory private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Payload effect factory changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Payload effect factory protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=50,frame=88,alignment_words=0,slot_words=50,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
