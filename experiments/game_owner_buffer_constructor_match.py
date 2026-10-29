"""Owner buffer constructor: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_15190770','generated_1BA1D0'
ENTRY,ROM,BODY,SIZE=0x15190770,0x1BDC20,208,208
SOURCE='conker/src/game/generated_1BA1D0.c'
OBJECT='conker/build/src/game/generated_1BA1D0.c.o'
ASM='conker/asm/1BA1D0.s'
BUILD='conker/build/game-owner-buffer-constructor-match'
RODATA_SYMBOL=None
RAW_SHA='c50acbdeedfa5e49c6cbdf4616ead32da415538f74a3e1041ab78a61d37d966f'
SNAPSHOT_SHA='d981ca2f84779311306a64eca5e47a7e8429818650f901691514c63a7cc289aa'
BEFORE_ELF_SHA='b8c35254472ac16519fa663b71c395823c265508a604f2bf5f0fcae50c07d44e'
TRUTH_SHA='6fd5d3e16b84cf30727cb29b64aa8cd9e29c807f8b14084de4333ea67c7fa052'
BINDINGS={56: [('R_MIPS_26', 'func_15191B8C')], 96: [('R_MIPS_26', 'func_15167A68')], 128: [('R_MIPS_26', 'memcpy')], 164: [('R_MIPS_26', 'bzero')], 172: [('R_MIPS_26', 'func_151D8E20')]}
HEADERS='#include <ultra64.h>\n#include "structs.h"\nvoid func_15191B8C(s32, u8);\nvoid *func_15167A68(s32, s32, s32, s32, u8, u8);\nvoid *memcpy(void *, const void *, u32);\nu8 func_151D8E20(void);\ntypedef struct {\n    u8 *owner;\n    u8 owner_id;\n    u8 padding[7];\n} OwnerBufferNotice1BA1D0;\n'
DECLARATIONS='void func_15191B8C(s32, u8);\nvoid *func_15167A68(s32, s32, s32, s32, u8, u8);\nvoid *memcpy(void *, const void *, u32);\nu8 func_151D8E20(void);\ntypedef struct {\n    u8 *owner;\n    u8 owner_id;\n    u8 padding[7];\n} OwnerBufferNotice1BA1D0;\n'
SELECTED='/* Notify the owner, then allocate and initialize its payload buffer. */\nvoid *func_15190770(struct185 *payload, s32 extraBytes, u8 priority, s32 context) {\n    OwnerBufferNotice1BA1D0 notice;\n    u8 *created;\n\n    notice.owner = (u8 *)payload->unk0;\n    notice.owner_id = ((u8 *)payload->unk0)[0x3B];\n    func_15191B8C((s32)&notice, 14);\n    created = func_15167A68(0x20, context, extraBytes + 0x300, 1, priority, 1);\n    if (created == NULL) {\n        return NULL;\n    }\n    memcpy(created + 0x10, payload, 12);\n    *(u8 **)(created + 0x24) = created + 0x30;\n    *(u8 **)(created + 0x28) = created + 0x300;\n    *(s32 *)(created + 0x20) = 0;\n    *(f32 *)(created + 0x1C) = 0.0f;\n    bzero(created + 0x30, 0x2D0);\n    created[0x2C] = func_151D8E20();\n    return created;\n}\n'

def check_owner_diagnostics(text):
    pattern=r'cfe: Warning 712: [^\n]+, line [0-9]+: illegal combination of pointer and integer\n     (func_[0-9A-F]+)\(arg0\);\n ------------------\^\n'
    names=re.findall(pattern,text)
    if names!=['func_1518E4A0','func_1518E4A0','func_15190454','func_15190454'] or re.sub(pattern,'',text):raise ValueError('Unexpected owner buffer constructor diagnostics')
    return len(names)


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=208 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Owner buffer constructor body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_15190770() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Owner buffer constructor placeholder changed')
    if before.count('func_15190770(payload, 0, record[0xC], record[1]);')!=1:raise ValueError('Buffer constructor C caller changed')
    return before.replace('#include <ultra64.h>\n','#include <ultra64.h>\n#include \"structs.h\"\n',1).replace(stub,DECLARATIONS+SELECTED.strip(),1).replace('func_15190770(payload, 0, record[0xC], record[1]);','func_15190770((struct185 *)payload, 0, record[0xC], record[1]);')


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Owner buffer constructor snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Owner buffer constructor frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Owner buffer constructor predecessor changed')
    return values

OTHER_SOURCE='conker/src/game/done/game_3F560.c'
OTHER_OBJECT='conker/build/src/game/done/game_3F560.c.o'

def recovered_caller(before):
    needle='#include "variables.h"\n'
    if before.count(needle)!=1 or 'void *func_15190770('in before:raise ValueError('Buffer constructor ancillary caller changed')
    return before.replace(needle,needle+'\n/* Shared owner-buffer constructor contract. */\nvoid *func_15190770(struct185 *, s32, u8, s32);\n',1)

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    if installed:changes[OTHER_SOURCE]=recovered_caller(values[OTHER_SOURCE].decode()).encode()
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Owner buffer constructor live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Owner buffer constructor frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Owner buffer constructor original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Owner buffer constructor strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Owner buffer constructor named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
    if sha(before)!='e800c51d09743626c1f1c510d66940511b7ce848746e8add05d95be041ec4be1':raise ValueError('Owner buffer constructor inherited guards changed')
    return before

def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)


ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_15190770.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-best-input.c","make-shadow/src/game/generated_1BA1D0.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_1BA1D0.c.o","make-shadow/src/game/generated_1BA1D0.c.o.padded.s",)

EVIDENCE=EVIDENCE+('proposed-caller.c', 'caller-declaration-proof.json', 'caller-before.o', 'caller-after.o', 'caller-make-shadow/src/game/done/game_3F560.c.o', 'caller-actual-Make-plan.txt', 'extra-caller-routes.json')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Owner buffer constructor artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner buffer constructor artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner buffer constructor raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Owner buffer constructor evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner buffer constructor Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1BA1D0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Owner buffer constructor Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Owner buffer constructor private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Owner buffer constructor changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner buffer constructor protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=52,frame=56,alignment_words=0,slot_words=52,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
