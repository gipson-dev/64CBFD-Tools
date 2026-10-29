"""Owner randomized packet: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_151D0058','generated_1FA770'
ENTRY,ROM,BODY,SIZE=0x151D0058,0x1FD508,208,208
SOURCE='conker/src/game/generated_1FA770.c'
OBJECT='conker/build/src/game/generated_1FA770.c.o'
ASM='conker/asm/1FA770.s'
BUILD='conker/build/game-owner-random-packet-match'
RODATA_SYMBOL=None
RAW_SHA='88e0d06e834bf1bf9d3be2834a144f223c8bf478a9635ee267673372b0d03643'
SNAPSHOT_SHA='6ec88ca1841b2cfe4b33ec499c3ccdb8a2b93fc92f8ca524fab365820d6f4632'
BEFORE_ELF_SHA='ae49e847d3cda56030e290efc7838489dd4621ca19ad3a793322ec56c57e6b26'
TRUTH_SHA='e67e4ae5f750756dcbeb4238f269ec1caad38f3b585d207d8e069c110072fdc1'
BINDINGS={76: [('R_MIPS_26', 'func_150ADA20')], 160: [('R_MIPS_26', 'func_15149130')], 180: [('R_MIPS_26', 'memcpy')]}
HEADERS='#include <ultra64.h>\ntypedef struct {\n    u8 *owner;\n    u8 ownerId;\n    u8 reserved0;\n    u16 flags;\n    f32 midpoint;\n    u8 randomByte;\n    u8 variant;\n    u8 reserved1[2];\n} OwnerRandomPacket;\ns32 func_150ADA20(void);\nvoid *func_15149130(s16, s8, s8, s8, u8, u8, s32, u8, s32);\nvoid *memcpy(void *, const void *, u32);\n'
DECLARATIONS='typedef struct {\n    u8 *owner;\n    u8 ownerId;\n    u8 reserved0;\n    u16 flags;\n    f32 midpoint;\n    u8 randomByte;\n    u8 variant;\n    u8 reserved1[2];\n} OwnerRandomPacket;\ns32 func_150ADA20(void);\nvoid *func_15149130(s16, s8, s8, s8, u8, u8, s32, u8, s32);\nvoid *memcpy(void *, const void *, u32);\n'
SELECTED='/* Capture owner state and submit a randomized sixteen-byte effect packet. */\nvoid func_151D0058(void *owner, u8 variant, u8 priority, s32 context) {\n    u8 *effect;\n    OwnerRandomPacket packet;\n\n    packet.owner = owner;\n    packet.ownerId = ((u8 *)owner)[0x3B];\n    packet.midpoint = (*(f32 *)((u8 *)owner + 0x150) + *(f32 *)((u8 *)owner + 0x14C)) * 0.5f;\n    packet.variant = variant;\n    packet.randomByte = (u32)func_150ADA20() % 56U + 200;\n    packet.flags = *(u16 *)((u8 *)owner + 0x84);\n    effect = func_15149130(300, -1, 0x61, 4, 0, 0x31, sizeof(packet), priority, context);\n    if (effect != NULL) {\n        memcpy(effect + 0x28, &packet, sizeof(packet));\n    }\n}\n'

def check_owner_diagnostics(text):
    value=re.sub(r'build/[^\n]+?, line \d+:','OWNER:',text)
    if value!='cfe: Warning 712: OWNER: illegal combination of pointer and integer\n     func_151D0ED8(arg0);\n ------------------^\ncfe: Warning 712: OWNER: illegal combination of pointer and integer\n     func_151D0ED8(arg0);\n ------------------^\ncfe: Warning 712: OWNER: illegal combination of pointer and integer\n     func_151D10E4(arg0, arg1, 0);\n ------------------^\ncfe: Warning 712: OWNER: illegal combination of pointer and integer\n     func_151D10E4(arg0, arg1, 1);\n ------------------^\ncfe: Warning 712: OWNER: illegal combination of pointer and integer\n     func_151D1368(arg0);\n ------------------^\ncfe: Warning 712: OWNER: illegal combination of pointer and integer\n     func_151D1368(arg0);\n ------------------^\ncfe: Warning 712: OWNER: illegal combination of pointer and integer\n     func_151D223C(arg0);\n ------------------^\ncfe: Warning 712: OWNER: illegal combination of pointer and integer\n     func_151D223C(arg0);\n ------------------^\n':raise ValueError('Unexpected randomized-packet owner diagnostics')
    return 8

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=208 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Owner randomized packet body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_151D0058() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Owner randomized packet placeholder changed')
    return before.replace(stub,(DECLARATIONS+SELECTED).strip())


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Owner randomized packet snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Owner randomized packet frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Owner randomized packet predecessor changed')
    return values

OTHER_SOURCE='conker/src/game_981E0.c'
OTHER_OBJECT='conker/build/src/game_981E0.c.o'
def recovered_caller(before):
    needle='void func_15192800(void *, s32);'
    if before.count(needle)!=1:raise ValueError('Random-packet caller declaration anchor changed')
    return before.replace(needle,needle+'\nvoid func_151D0058(void *, u8, u8, s32);',1).replace('(arg0 - 0x55) & 0xFF','(u8)(arg0 - 0x55)')

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    if installed:changes[OTHER_SOURCE]=recovered_caller(values[OTHER_SOURCE].decode()).encode()
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Owner randomized packet live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Owner randomized packet strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    named={}
    for pos,name,fields,_ in symbol_rows(before):named.setdefault(name,[]).append((pos,fields))
    rows=named[FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Owner randomized packet original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Owner randomized packet image differs from body and extent prediction')
    expected=Counter((n,f[1],208 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Owner randomized packet named ELF definitions changed')

NEW_GUARDS=[]
def guard_manifest(before):
    if sha(before)!='84c233dfd374f8ba8b4f66dca69b180bc2b8b3813b7a1a594d72f88130ba0306':raise ValueError('Inherited guard bytes changed')
    return before
def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_151D0058.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game/generated_1FA770.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_1FA770.c.o","make-shadow/src/game/generated_1FA770.c.o.padded.s",)

EVIDENCE=EVIDENCE+('selected-best-input.c', 'proposed-caller.c', 'caller-declaration-proof.json', 'caller-before.o', 'caller-after.o', 'caller-make-shadow/src/game_981E0.c.o', 'caller-actual-Make-plan.txt', 'private-behavior-v5.json', 'private-native-v6.json', 'private-routes-v10.json')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Owner randomized packet artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner randomized packet artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner randomized packet raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Owner randomized packet evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner randomized packet Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1FA770.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Owner randomized packet Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Owner randomized packet private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Owner randomized packet changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner randomized packet protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=52,frame=80,alignment_words=0,slot_words=52,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

FACTORY,COPY=0x15149130,0x10022EC0
