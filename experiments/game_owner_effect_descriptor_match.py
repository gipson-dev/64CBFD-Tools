"""Owner effect descriptor: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_151AF270','generated_1D92F0'
ENTRY,ROM,BODY,SIZE=0x151AF270,0x1DC720,200,200
SOURCE='conker/src/game/generated_1D92F0.c'
OBJECT='conker/build/src/game/generated_1D92F0.c.o'
ASM='conker/asm/1D92F0.s'
BUILD='conker/build/game-owner-effect-descriptor-match'
RODATA_SYMBOL=None
RAW_SHA='4cc2a252a2c7b8d8f884d655c489b5b7ec99fca7ae90b05a89208210e84d2e7d'
SNAPSHOT_SHA='79f0c1e09c0724e27141acc911964dad749a8b27ce15e1415b1257eed7cf0108'
BEFORE_ELF_SHA='712971ca8c175d1ccaa01a4a1ae99e00065d15835ebc66a6e508d62b40ba6368'
TRUTH_SHA='7c97225c4fe5c1139ee4120ea35f919638018a8d1adb9a119f659fc547d3cbd5'
BINDINGS={44: [('R_MIPS_26', 'func_1516962C')], 68: [('R_MIPS_HI16', 'D_800A9DCC')], 76: [('R_MIPS_LO16', 'D_800A9DCC')], 80: [('R_MIPS_HI16', 'D_800A9DD0')], 84: [('R_MIPS_LO16', 'D_800A9DD0')], 176: [('R_MIPS_26', 'func_1513418C')]}
HEADERS='#include <ultra64.h>\n\ntypedef struct {\n    u32 zero0, zero4;\n    u8 ownerIdentity, reserved09[3];\n    u8 *owner;\n    u8 attachment, reserved11[3];\n    f32 vector[3];\n    f32 value20, value24;\n    s16 duration;\n    u8 flags, kind;\n    s8 callback;\n    u8 mode;\n} OwnerEffectDescriptor1D92F0;\n\nextern f32 D_800A9DCC, D_800A9DD0;\nvoid func_1516962C(s32, void *, u8);\nvoid *func_1513418C(void *, s32, u8, s32);\n\n'
DECLARATIONS='typedef struct {\n    u32 zero0, zero4;\n    u8 ownerIdentity, reserved09[3];\n    u8 *owner;\n    u8 attachment, reserved11[3];\n    f32 vector[3];\n    f32 value20, value24;\n    s16 duration;\n    u8 flags, kind;\n    s8 callback;\n    u8 mode;\n} OwnerEffectDescriptor1D92F0;\n\nextern f32 D_800A9DCC, D_800A9DD0;\nvoid func_1516962C(s32, void *, u8);\nvoid *func_1513418C(void *, s32, u8, s32);\n\n'
SELECTED='/* Notify the owner before constructing its attached effect descriptor. */\nvoid *func_151AF270(u8 *owner, u8 selector, s32 category) {\n    void *created;\n    OwnerEffectDescriptor1D92F0 descriptor;\n\n    if (owner == NULL) {\n        return NULL;\n    }\n    func_1516962C(40, owner, 22);\n    descriptor.zero0 = 0;\n    descriptor.zero4 = 0;\n    descriptor.ownerIdentity = owner[0x3B];\n    descriptor.owner = owner;\n    descriptor.attachment = 1;\n    descriptor.vector[0] = 0.0f;\n    descriptor.vector[1] = 0.0f;\n    descriptor.vector[2] = 0.0f;\n    descriptor.value20 = D_800A9DCC;\n    descriptor.value24 = D_800A9DD0;\n    descriptor.flags = 6;\n    descriptor.duration = 320;\n    descriptor.kind = 10;\n    descriptor.callback = -1;\n    descriptor.mode = 9;\n    created = func_1513418C(&descriptor, 0, selector, category);\n    return created;\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected owner-effect-descriptor owner diagnostics')
    return 0

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=200 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Owner effect descriptor body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_151AF270() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Owner effect descriptor placeholder changed')
    return before.replace(stub,(DECLARATIONS+SELECTED).strip())


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Owner effect descriptor snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Owner effect descriptor frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Owner effect descriptor predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={CALLER_SOURCE:recovered_caller(values[CALLER_SOURCE].decode()).encode(),'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Owner effect descriptor live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Owner effect descriptor strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    named={}
    for pos,name,fields,_ in symbol_rows(before):named.setdefault(name,[]).append((pos,fields))
    rows=named[FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Owner effect descriptor original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    # Closed symbol/string bucket swaps caused by the new references. Every
    # named definition and the complete serialized span are checked explicitly.
    rows={n:(p,f,loc)for p,n,f,loc in symbol_rows(before)}
    definitions={'D_800A9DD0':(0x800A9DD0,0,16,0,65521),'D_8009CDD0':(0x8009CDD0,0,16,0,6),
        'D_800A9DCC':(0x800A9DCC,0,16,0,65521),'D_800AABFC':(0x800AABFC,0,16,0,65521),
        'D_800994AC':(0x800994AC,0,16,0,65521),'D_8009EEAC':(0x8009EEAC,0,16,0,6)}
    for names in (('D_800A9DD0','D_8009CDD0'),('D_800A9DCC','D_800AABFC'),('D_800994AC','D_8009EEAC')):
        first,second=[rows[n]for n in names]
        if second[0]-first[0]!=16 or second[2]-first[2]!=11 or second[1][0]-first[1][0]!=11:
            raise ValueError('Owner effect closed symbol slots changed')
        for name,(pos,f,loc)in zip(names,(first,second)):
            if f[1:]!=definitions[name]or before[loc:loc+11]!=name.encode()+b'\0':
                raise ValueError('Owner effect named symbol changed: '+name)
        for dest,src,name in ((first,second,names[1]),(second,first,names[0])):
            result[dest[0]:dest[0]+16]=before[src[0]:src[0]+16]
            struct.pack_into('>I',result,dest[0],dest[1][0])
            result[dest[2]:dest[2]+11]=name.encode()+b'\0'
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Owner effect descriptor image differs from body and extent prediction')
    expected=Counter((n,f[1],200 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Owner effect descriptor named ELF definitions changed')

NEW_GUARDS=[]
def guard_manifest(before):
    if sha(before)!='1678dac601e1def3df3c6438b7a8b4bb0914ce5ef73a929921f12916f7ead9f2':raise ValueError('Inherited guard bytes changed')
    return before
def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)

ARTIFACTS=('qualified-caller-padded.o','proposed-caller.c','before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_151AF270.o','first-linked.elf')
EVIDENCE=("caller-Make-plan.txt","caller-Make-commands.json","caller-make-shadow/src/game/generated_1C1150.c.o","caller-qualification.json","before-caller.c","before-caller.o","before-caller-processed.c","before-caller-diagnostics.txt","after-caller.c","after-caller.o","after-caller-processed.c","after-caller-diagnostics.txt","proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game/generated_1D92F0.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_1D92F0.c.o","make-shadow/src/game/generated_1D92F0.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Owner effect descriptor artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner effect descriptor artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner effect descriptor raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Owner effect descriptor evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner effect descriptor Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1D92F0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Owner effect descriptor Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Owner effect descriptor private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Owner effect descriptor changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner effect descriptor protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=50,frame=80,alignment_words=0,slot_words=50,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q


CALLER_SOURCE='conker/src/game/generated_1C1150.c'
CALLER_OBJECT='conker/build/src/game/generated_1C1150.c.o'
CALLER_ASM='conker/asm/1C1150.s'
def recovered_caller(before):
    marker='#include <ultra64.h>\n'
    if before.count(marker)!=1 or 'void *func_151AF270' in before:raise ValueError('Caller declaration precondition changed')
    return before.replace(marker,marker+'\nvoid *func_151AF270(u8 *, u8, s32);\n',1)
