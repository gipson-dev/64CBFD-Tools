"""Owner variant descriptor: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_150D10E4','generated_FDD70'
ENTRY,ROM,BODY,SIZE=0x150D10E4,0xFE594,208,208
SOURCE='conker/src/game/generated_FDD70.c'
OBJECT='conker/build/src/game/generated_FDD70.c.o'
ASM='conker/asm/FDD70.s'
BUILD='conker/build/game-owner-variant-descriptor-match'
RODATA_SYMBOL=None
PARENT=0x151951E0
RAW_SHA='2384616d6715080829c7f65476e7c5ac276e0ccc311d69ba04b9f99ed1079478'
SNAPSHOT_SHA='9a3f5e14a4bb0bd51c97136bedcef9df91b6a090a6e47648dc91013f5b2aea11'
BEFORE_ELF_SHA='ead9c7a16e0b4227f788916bbf6498b99040aa424634394d85a0ecab8bc3e1a0'
TRUTH_SHA='e39f076e374f91e6b2a38d777f9bf2db2d73f4ea6ae5084999d221d7325de8e0'
BINDINGS={92: [('R_MIPS_HI16', 'D_800A0890')], 96: [('R_MIPS_LO16', 'D_800A0890')], 184: [('R_MIPS_26', 'func_15134DAC')]}
HEADERS='#include <ultra64.h>\nextern f32 D_800A0890;\nvoid *func_15134DAC(s32, s32);\ntypedef struct {\n    u8 owner_id;\n    u8 pad1[3];\n    u8 *owner;\n    u8 attachmentIndex;\n    u8 pad9[3];\n    f32 zero0;\n    f32 zero1;\n    f32 zero2;\n    f32 zero3;\n    f32 value1C;\n    f32 value20;\n    u8 mode;\n    u8 pad25;\n    s16 activeFrames;\n    s16 restartDelay;\n    s16 lifetime;\n    s16 value2C;\n    s8 startCallback;\n    s8 transformCallback;\n    s8 updateCallback;\n    u8 pad31[3];\n    f32 rate;\n    u8 flags;\n    s8 finishCallback;\n} OwnerVariantDescriptorFDD70;\n\n'
DECLARATIONS='extern f32 D_800A0890;\nvoid *func_15134DAC(s32, s32);\ntypedef struct {\n    u8 owner_id;\n    u8 pad1[3];\n    u8 *owner;\n    u8 attachmentIndex;\n    u8 pad9[3];\n    f32 zero0;\n    f32 zero1;\n    f32 zero2;\n    f32 zero3;\n    f32 value1C;\n    f32 value20;\n    u8 mode;\n    u8 pad25;\n    s16 activeFrames;\n    s16 restartDelay;\n    s16 lifetime;\n    s16 value2C;\n    s8 startCallback;\n    s8 transformCallback;\n    s8 updateCallback;\n    u8 pad31[3];\n    f32 rate;\n    u8 flags;\n    s8 finishCallback;\n} OwnerVariantDescriptorFDD70;\n\n'
SELECTED='/* Construct an owner-attached effect with a variant-dependent signed offset. */\nvoid *func_150D10E4(u8 *owner, u8 variant) {\n    OwnerVariantDescriptorFDD70 packet;\n    packet.owner_id = owner[0x3B];\n    packet.owner = owner;\n    packet.attachmentIndex = 0;\n    packet.zero0 = 0.0f;\n    packet.zero1 = 0.0f;\n    packet.zero2 = 0.0f;\n    packet.zero3 = 0.0f;\n    packet.value1C = variant != 0 ? -30.0f : 30.0f;\n    packet.value20 = 0.0f;\n    packet.mode = 2;\n    packet.activeFrames = 50;\n    packet.restartDelay = 22;\n    packet.lifetime = 2000;\n    packet.value2C = 0;\n    packet.startCallback = 6;\n    packet.transformCallback = 7;\n    packet.updateCallback = -1;\n    packet.rate = D_800A0890;\n    packet.flags = 0;\n    packet.finishCallback = -1;\n    return func_15134DAC((s32)&packet, 0);\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected Owner variant descriptor owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=208 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Owner variant descriptor body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_150D10E4() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Owner variant descriptor placeholder changed')
    return before.replace(stub,DECLARATIONS+SELECTED.strip(),1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Owner variant descriptor snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Owner variant descriptor frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Owner variant descriptor predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Owner variant descriptor live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Owner variant descriptor frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Owner variant descriptor original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    # Adding the original constant reference swaps one existing GNU symbol bucket.
    # Require the exact original definitions and both contiguous serialized slots.
    named={n:(p,f,loc)for p,n,f,loc in symbol_rows(before)}
    names=('D_8009943C','D_8009EE3C');group=[named[n]for n in names]
    for i,(n,(pos,f,loc))in enumerate(zip(names,group)):
        if f[1:]!=(int(n[2:],16),0,16,0,65521 if i==0 else 6):raise ValueError('Variant descriptor symbol definition changed')
        if pos!=group[0][0]+16*i or loc!=group[0][2]+11*i or before[loc:loc+11]!=n.encode()+b'\0':raise ValueError('Variant descriptor symbol bucket changed')
    for dest,origin,n in zip(group,reversed(group),reversed(names)):
        result[dest[0]:dest[0]+16]=before[origin[0]:origin[0]+16]
        struct.pack_into('>I',result,dest[0],dest[1][0]);result[dest[2]:dest[2]+11]=n.encode()+b'\0'
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Owner variant descriptor strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Owner variant descriptor named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
    if sha(before)!='e800c51d09743626c1f1c510d66940511b7ce848746e8add05d95be041ec4be1':raise ValueError('Owner variant descriptor inherited guards changed')
    return before

def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)


ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_150D10E4.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-best-input.c","make-shadow/src/game/generated_FDD70.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_FDD70.c.o","make-shadow/src/game/generated_FDD70.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Owner variant descriptor artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner variant descriptor artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner variant descriptor raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Owner variant descriptor evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner variant descriptor Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_FDD70.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Owner variant descriptor Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Owner variant descriptor private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Owner variant descriptor changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner variant descriptor protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=52,frame=88,alignment_words=0,slot_words=52,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
