"""Record effect packet: direct C, actual ABI and literal owner/image audit."""
from pathlib import Path
import hashlib,json,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_151A18DC','generated_1CC440'
ENTRY,ROM,BODY,SIZE=0x151A18DC,0x1CED8C,188,188
SOURCE='conker/src/game/generated_1CC440.c'
OBJECT='conker/build/src/game/generated_1CC440.c.o'
ASM='conker/asm/1CC440.s'
BUILD='conker/build/game-record-effect-packet-match'
RAW_SHA="81f140bfef6a9e5df21cc4aef94f15238658336e9b46d9997ea957852e6853eb"
SNAPSHOT_SHA="de21e1204b826ddfd2b07b96bbc1c4ab66923e6d403c718bc937df7c3b745477"
BEFORE_ELF_SHA="bd9f7b5c27bdd3cff531753735c1640eb04e2b27b94afe265b17519bc3eb4842"
TRUTH_SHA="89fe43a3f88509986fd6cdc417dce94d0db5f707c95c2b62cea5e0dcd0681b34"
FACTORY,CONSTRUCTOR,COPY=0x151491F4,0x15149130,0x10022EC0
ALLOC,ZERO,HEAP,REGISTER=0x15167A68,0x100226F0,0x10003C6C,0x15168A4C
CALLER,TABLE,UPDATE_TABLE,TICKS=0x15149264,0x8008A4C0,0x8008A4E8,0x800BE9E4
BINDINGS={140:[("R_MIPS_26","func_151491F4")],160:[("R_MIPS_26","memcpy")]}
HEADERS="#include <ultra64.h>\n#include \"structs.h\"\n"
DECLARATIONS="typedef struct {\n    f32 x, y, z;\n} EffectPacketPosition1CC440;\n\ntypedef struct {\n    EffectPacketPosition1CC440 position;\n    f32 sourceValueA;\n    f32 phase;\n    f32 sourceValueB;\n    s16 parameters[4];\n} RecordEffectPacket1CC440;\n\nstruct260 *func_151491F4(s16, s8, s8, u8, u8, s32, u8, s32);\nvoid *memcpy(void *, const void *, u32);\n\n"
SELECTED="/* Spawn an effect from the record's captured 32-byte parameter packet. */\nvoid func_151A18DC(struct260 *record) {\n    struct260 *effect;\n    RecordEffectPacket1CC440 packet;\n\n    packet.position = *(EffectPacketPosition1CC440 *)((u8 *)record + 0x28);\n    packet.sourceValueA = *(f32 *)((u8 *)record + 0x34);\n    packet.phase = 0.0f;\n    packet.sourceValueB = *(f32 *)((u8 *)record + 0x38);\n    packet.parameters[0] = *(s16 *)((u8 *)record + 0x3E);\n    packet.parameters[1] = *(s16 *)((u8 *)record + 0x40);\n    packet.parameters[2] = *(s16 *)((u8 *)record + 0x42);\n    packet.parameters[3] = *(s16 *)((u8 *)record + 0x44);\n    effect = func_151491F4(*(s16 *)((u8 *)record + 0x3C), -1, 3, 1, 0,\n                          sizeof(packet), ((u8 *)record)[0xC], ((u8 *)record)[1]);\n    if (effect != NULL) {\n        memcpy((u8 *)effect + 0x28, &packet, sizeof(packet));\n    }\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Record effect packet body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub="s32 func_151A18DC() {\n    return 0;\n}"
    if before.count(stub)!=1:raise ValueError("Record packet placeholder changed")
    return before.replace("#include <ultra64.h>","#include <ultra64.h>"+chr(10)+'#include "structs.h"',1).replace(stub,DECLARATIONS+SELECTED,1)

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Record effect packet snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Record effect packet frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Record effect packet predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Record effect packet live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Record effect packet strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Record effect packet original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Record effect packet image differs from body and extent prediction')
    expected=Counter((n,f[1],188 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Record effect packet named ELF definitions changed')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_151A18DC.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","make-shadow/src/game/generated_1CC440.c","make-shadow/src/game/generated_1CC440.c.o","make-shadow/src/game/generated_1CC440.c.o.compact","make-shadow/src/game/generated_1CC440.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Record effect packet artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record effect packet artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record effect packet raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Record effect packet evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record effect packet Make/diagnostics evidence changed: '+name)
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner','selected')):raise ValueError('Record effect packet expected empty diagnostics')
    if(output/'make-shadow/src/game/generated_1CC440.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Record effect packet Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Record effect packet private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Record effect packet changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Record effect packet protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=47,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
