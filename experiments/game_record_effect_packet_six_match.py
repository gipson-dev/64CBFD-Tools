"""Six-parameter effect packet: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_151A1EE8','generated_1CC440'
ENTRY,ROM,BODY,SIZE=0x151A1EE8,0x1CF398,204,204
SOURCE='conker/src/game/generated_1CC440.c'
OBJECT='conker/build/src/game/generated_1CC440.c.o'
ASM='conker/asm/1CC440.s'
BUILD='conker/build/game-record-effect-packet-six-match'
RODATA_SYMBOL=None
FACTORY,CONSTRUCTOR,COPY=0x151491F4,0x15149130,0x10022EC0
ALLOC,ZERO,HEAP,REGISTER=0x15167A68,0x100226F0,0x10003C6C,0x15168A4C
CALLER,TABLE,UPDATE_TABLE,TICKS=0x15149264,0x8008A4C0,0x8008A4E8,0x800BE9E4
RAW_SHA='943e575a9ae8e9a80c2eff4eacd223926fc34b15d1430f731b146f20da1fab99'
SNAPSHOT_SHA='e0ff11d00b2a5b5dd9ab9331b40cbafdf3bf183e3d26c38df93bf7bf1c4d2926'
BEFORE_ELF_SHA='147d665e2013a9ef65c6ac40471002b8a08b0292323b6fbd933788a8bbd1b1df'
TRUTH_SHA='cc5c241255b023bb89146b25cd815ba05c4d1511a9897c097abe368bb713ebdd'
BINDINGS={156: [('R_MIPS_26', 'func_151491F4')], 176: [('R_MIPS_26', 'memcpy')]}
HEADERS='#include <ultra64.h>\n#include "structs.h"\ntypedef struct {\n    f32 x, y, z;\n} EffectPacketPosition1CC440;\n\n\n\nstruct260 *func_151491F4(s16, s8, s8, u8, u8, s32, u8, s32);\nvoid *memcpy(void *, const void *, u32);\n\n'
DECLARATIONS='typedef struct {\n    EffectPacketPosition1CC440 position;\n    f32 sourceValueA;\n    f32 phase;\n    f32 sourceValueB;\n    s16 parameters[6];\n} RecordEffectPacketSix1CC440;\n\n'
SELECTED="/* Spawn an effect from the record's captured 36-byte parameter packet. */\nvoid func_151A1EE8(struct260 *record) {\n    struct260 *effect;\n    RecordEffectPacketSix1CC440 packet;\n    u8 *bytes = (u8 *)record;\n\n    packet.position = *(EffectPacketPosition1CC440 *)(bytes + 0x28);\n    packet.sourceValueA = *(f32 *)(bytes + 0x34);\n    packet.phase = 0.0f;\n    packet.sourceValueB = *(f32 *)(bytes + 0x38);\n    packet.parameters[0] = *(s16 *)(bytes + 0x3E);\n    packet.parameters[1] = *(s16 *)(bytes + 0x40);\n    packet.parameters[2] = *(s16 *)(bytes + 0x42);\n    packet.parameters[3] = *(s16 *)(bytes + 0x44);\n    packet.parameters[4] = *(s16 *)(bytes + 0x46);\n    packet.parameters[5] = *(s16 *)(bytes + 0x48);\n    effect = func_151491F4(*(s16 *)(bytes + 0x3C), -1, 4, 1, 0,\n                          sizeof(packet), bytes[0xC], bytes[1]);\n    if (effect != NULL) {\n        memcpy((u8 *)effect + 0x28, &packet, sizeof(packet));\n    }\n}\n"

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected six-parameter packet owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=204 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Six-parameter effect packet body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_151A1EE8() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Six-parameter effect packet placeholder changed')
    return before.replace(stub,DECLARATIONS+SELECTED.strip(),1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Six-parameter effect packet snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Six-parameter effect packet frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Six-parameter effect packet predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Six-parameter effect packet live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Six-parameter effect packet frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Six-parameter effect packet original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Six-parameter effect packet strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Six-parameter effect packet named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
    if sha(before)!='1e58e8b29313c9ffe2b784379c53af9fdc8eb9152c9bb3d1e1a5fb832a5d26b6':raise ValueError('Six-parameter effect packet inherited guards changed')
    return before

def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)


ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_151A1EE8.o','first-linked.elf')
EVIDENCE=("make-shadow/src/game/generated_1CC440.c","proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-best-input.c","make-shadow/src/game/generated_1CC440.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_1CC440.c.o","make-shadow/src/game/generated_1CC440.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Six-parameter effect packet artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Six-parameter effect packet artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Six-parameter effect packet raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Six-parameter effect packet evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Six-parameter effect packet Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1CC440.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Six-parameter effect packet Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Six-parameter effect packet private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Six-parameter effect packet changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Six-parameter effect packet protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=51,frame=96,alignment_words=0,slot_words=51,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
